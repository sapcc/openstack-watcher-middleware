# Copyright 2018 SAP SE
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import yaml
import time

from datadog.dogstatsd import DogStatsd
from pycadf import cadftaxonomy as taxonomy
from webob import Request

from . import common
from . import errors
from . import cadf_strategy as strategies

logging.basicConfig(level=logging.ERROR, format='%(asctime)-15s %(message)s')


# Map of service types and strategies to determine target type URI and action
# Usually the base strategy is sufficient
STRATEGIES = {
    'object-store': strategies.SwiftCADFStrategy
}


class OpenStackWatcherMiddleware(object):
    """
    OpenStack Watcher Middleware

    Watches OpenStack traffic and classifies according to CADF standard
    """
    def __init__(self, app, config, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.app = app
        self.wsgi_config = config
        self.watcher_config = {}

        self.cadf_service_name = self.wsgi_config.get('cadf_service_name', None)
        self.service_type = self.wsgi_config.get('service_type', taxonomy.UNKNOWN)
        # get the project uid from the request path or from the token (default)
        self.is_project_id_from_path = common.string_to_bool(
            self.wsgi_config.get('target_project_id_from_path', 'False')
        )
        # get the project id from the service catalog (see documentation on keystone auth_token middleware)
        self.is_project_id_from_service_catalog = common.string_to_bool(
            self.wsgi_config.get('target_project_id_from_service_catalog', 'False')
        )

        # whether to include the target project id in the metrics
        self.is_include_target_project_id_in_metric = common.string_to_bool(
            self.wsgi_config.get('include_target_project_id_in_metric', 'True')
        )
        # whether to include the target domain id in the metrics
        self.is_include_target_domain_id_in_metric = common.string_to_bool(
            self.wsgi_config.get('include_target_domain_id_in_metric', 'True')
        )
        # whether to include the initiator user id in the metrics
        self.is_include_initiator_user_id_in_metric = common.string_to_bool(
            self.wsgi_config.get('include_initiator_user_id_in_metric', 'False')
        )

        config_file_path = config.get('config_file', None)
        if config_file_path:
            try:
                self.watcher_config = load_config(config_file_path)
            except errors.ConfigError as e:
                self.logger.debug("custom actions not available: %s", str(e))

        custom_action_config = self.watcher_config.get('custom_actions', {})
        path_keywords = self.watcher_config.get('path_keywords', {})
        keyword_exclusions = self.watcher_config.get('keyword_exclusions', {})
        regex_mapping = self.watcher_config.get('regex_path_mapping', {})

        # init the strategy used to determine the target type uri
        strat = STRATEGIES.get(
            self.service_type,
            strategies.BaseCADFStrategy
        )

        # set custom prefix to target type URI or use defaults
        target_type_uri_prefix = common.SERVICE_TYPE_CADF_PREFIX_MAP.get(
            self.service_type,
            'service/{0}'.format(self.service_type)
        )

        if self.cadf_service_name:
            target_type_uri_prefix = self.cadf_service_name

        strategy = strat(
            target_type_uri_prefix=target_type_uri_prefix,
            path_keywords=path_keywords,
            keyword_exclusions=keyword_exclusions,
            custom_action_config=custom_action_config,
            regex_mapping=regex_mapping
        )

        self.strategy = strategy

        self.metric_client = DogStatsd(
            host=self.wsgi_config.get("statsd_host", "127.0.0.1"),
            port=int(self.wsgi_config.get("statsd_port", 9125)),
            namespace=self.wsgi_config.get("statsd_namespace", "openstack_watcher")
        )

    @classmethod
    def factory(cls, global_config, **local_config):
        conf = global_config.copy()
        conf.update(local_config)

        def watcher(app):
            return cls(app, conf)
        return watcher

    def __call__(self, environ, start_response):
        """
        WSGI entry point. Wraps environ in webob.Request

        :param environ: the WSGI environment dict
        :param start_response: WSGI callable
        """

        # capture start timestamp
        start = time.time()

        req = Request(environ)

        # determine initiator based on token context
        initiator_project_id = environ.get('HTTP_X_PROJECT_ID', taxonomy.UNKNOWN)
        initiator_project_name = environ.get('HTTP_X_PROJECT_NAME', taxonomy.UNKNOWN)
        initiator_project_domain_id = environ.get('HTTP_X_PROJECT_DOMAIN_ID', taxonomy.UNKNOWN)
        initiator_project_domain_name = environ.get('HTTP_X_DOMAIN_NAME', taxonomy.UNKNOWN)
        initiator_domain_id = environ.get('HTTP_X_DOMAIN_ID', taxonomy.UNKNOWN)
        initiator_domain_name = environ.get('HTTP_X_DOMAIN_NAME', taxonomy.UNKNOWN)
        initiator_user_id = environ.get('HTTP_X_USER_ID', taxonomy.UNKNOWN)
        initiator_user_domain_id = environ.get('HTTP_X_USER_DOMAIN_ID', taxonomy.UNKNOWN)
        initiator_user_domain_name = environ.get('HTTP_X_USER_DOMAIN_NAME', taxonomy.UNKNOWN)
        initiator_host_address = req.client_addr or taxonomy.UNKNOWN

        # determine target based on request path or keystone.token_info
        target_project_id = taxonomy.UNKNOWN
        if self.is_project_id_from_path:
            target_project_id = self.get_target_project_uid_from_path(req.path)
        elif self.is_project_id_from_service_catalog:
            target_project_id = self.get_target_project_id_from_keystone_token_info(environ.get('keystone.token_info'))

        # default target_project_id to initiator_project_id if still unknown
        if not target_project_id or target_project_id == taxonomy.UNKNOWN:
            target_project_id = initiator_project_id

        # determine target.type_uri for request
        target_type_uri = self.determine_target_type_uri(req)

        # determine cadf_action for request. consider custom action config.
        cadf_action = self.determine_cadf_action(req, target_type_uri)

        # if authentication request consider project, domain and user in body
        if self.service_type == 'identity' and cadf_action == taxonomy.ACTION_AUTHENTICATE:
            initiator_project_id, initiator_domain_id, initiator_user_id = \
                self.get_project_domain_and_user_id_from_keystone_authentication_request(req)

        # set environ for initiator
        environ['WATCHER.INITIATOR_PROJECT_ID'] = initiator_project_id
        environ['WATCHER.INITIATOR_PROJECT_NAME'] = initiator_project_name
        environ['WATCHER.INITIATOR_PROJECT_DOMAIN_ID'] = initiator_project_domain_id
        environ['WATCHER.INIITATOR_PROJECT_DOMAIN_NAME'] = initiator_project_domain_name
        environ['WATCHER.INITIATOR_DOMAIN_ID'] = initiator_domain_id
        environ['WATCHER.INITIATOR_DOMAIN_NAME'] = initiator_domain_name
        environ['WATCHER.INITIATOR_USER_ID'] = initiator_user_id
        environ['WATCHER.INITIATOR_USER_DOMAIN_ID'] = initiator_user_domain_id
        environ['WATCHER.INITIATOR_USER_DOMAIN_NAME'] = initiator_user_domain_name
        environ['WATCHER.INITIATOR_HOST_ADDRESS'] = initiator_host_address

        # set environ for target
        environ['WATCHER.TARGET_PROJECT_ID'] = target_project_id
        environ['WATCHER.TARGET_TYPE_URI'] = target_type_uri

        # general cadf attributes
        environ['WATCHER.ACTION'] = cadf_action
        environ['WATCHER.SERVICE_TYPE'] = self.service_type
        environ['WATCHER.CADF_SERVICE_NAME'] = self.strategy.get_cadf_service_name()

        # labels applied to all metrics emitted by this middleware
        labels = [
            "service_name:{0}".format(self.strategy.get_cadf_service_name()),
            "service:{0}".format(self.service_type),
            "action:{0}".format(cadf_action),
            "target_type_uri:{0}".format(target_type_uri),
        ]

        # additional labels not needed in all metrics
        detail_labels = [
            "initiator_project_id:{0}".format(initiator_project_id),
            "initiator_domain_id:{0}".format(initiator_domain_id),
        ]
        detail_labels = labels + detail_labels

        # include the target project id in metric
        if self.is_include_target_project_id_in_metric:
            detail_labels.append(
                "target_project_id:{0}".format(target_project_id)
            )

        # include initiator user id
        if self.is_include_initiator_user_id_in_metric:
            detail_labels.append(
                "initiator_user_id:{0}".format(initiator_user_id)
            )

        # if swift request: determine target.container_id based on request path
        if common.is_swift_request(req.path) or self.service_type == 'object-store':
            _, target_container_id = self.get_target_account_container_id_from_request(req)
            environ['WATCHER.TARGET_CONTAINER_ID'] = target_container_id

        self.logger.debug(
            'got request with initiator_project_id: {0}, initiator_domain_id: {1}, initiator_user_id: {2}, '
            'target_project_id: {3}, action: {4}, target_type_uri: {5}'.format(
                initiator_project_id, initiator_domain_id, initiator_user_id, target_project_id,
                cadf_action, target_type_uri
            )
        )

        # capture the response status
        response_wrapper = {}

        try:
            def _start_response_wrapper(status, headers, exc_info=None):
                response_wrapper.update(status=status, headers=headers, exc_info=exc_info)
                return start_response(status, headers, exc_info)

            return self.app(environ, _start_response_wrapper)
        finally:
            try:
                self.metric_client.open_buffer()

                status = response_wrapper.get('status')
                if status:
                    status_code = status.split()[0]
                else:
                    status_code = 'none'

                labels.append("status:{0}".format(status_code))
                detail_labels.append("status:{0}".format(status_code))

                self.metric_client.timing('api_requests_duration_seconds', int(round(1000 * (time.time() - start))),
                                          tags=labels)
                self.metric_client.increment('api_requests_total', tags=detail_labels)
            except Exception as e:
                self.logger.debug("failed to submit metrics for %s: %s" % (str(labels), str(e)))
            finally:
                self.metric_client.close_buffer()

    def get_target_project_uid_from_path(self, path):
        """
        get the project uid from the path, which should look like
        ../v1.2/<project_uid>/.. or ../v1/AUTH_<project_uid>/..

        :param path: the request path containing a project uid
        :return: the project uid
        """
        project_uid = taxonomy.UNKNOWN
        try:
            if common.is_swift_request(path) and self.strategy.name == 'object-store':
                project_uid = self.strategy.get_swift_project_id_from_path(path)
            else:
                project_uid = common.get_project_id_from_os_path()
        finally:
            if project_uid == taxonomy.UNKNOWN:
                self.logger.debug("unable to obtain target.project_id from request path '{0}'".format(path))
            else:
                self.logger.debug("request path '{0}' contains target.project_id '{1}'".format(path, project_uid))
            return project_uid

    def get_target_project_id_from_keystone_token_info(self, token_info):
        """
        the token info dict contains the service catalog, in which the project specific
        endpoint urls per service can be found.

        :param token_info: token info dictionary
        :return: the project id or unknown
        """
        project_id = taxonomy.UNKNOWN
        try:
            service_catalog = token_info.get('token', {}).get('catalog', [])
            if not service_catalog:
                raise None

            for service in service_catalog:
                svc_type = service.get('type', None)
                if not svc_type or svc_type != self.service_type:
                    continue

                svc_endpoints = service.get('endpoints', None)
                if not svc_endpoints:
                    continue

                project_id = self._get_project_id_from_service_endpoints(svc_endpoints)
                if project_id:
                    break

        except Exception as e:
            self.logger.debug('unable to get target.project_id from service catalog: ', str(e))

        finally:
            if project_id == taxonomy.UNKNOWN:
                self.logger.debug(
                    "unable to get target.project_id for service type '{1}' from service catalog"
                    .format(project_id, self.service_type))
            else:
                self.logger.debug(
                    "got target.project_id '{0}' for service type '{1}' from service catalog"
                    .format(project_id, self.service_type))
            return project_id

    def _get_project_id_from_service_endpoints(self, endpoint_list, endpoint_type=None):
        """
        get the project id from an endpoint url for a given type | type = {public,internal,admin}

        :param endpoint_list: list of endpoints
        :param endpoint_type: optional endpoint type
        :return: the project id or unknown
        """
        project_id = taxonomy.UNKNOWN
        try:
            for endpoint in endpoint_list:
                url = endpoint.get('url', None)
                type = endpoint.get('interface', None)
                if not url or not type:
                    continue

                if self.strategy.name == 'object-store':
                    project_id = self.strategy.get_swift_project_id_from_path(url)
                else:
                    project_id = common.get_project_id_from_os_path(url)

                # break here if endpoint_type is given and types match
                if endpoint_type and endpoint_type.lower() == type.lower():
                    break
                # break here if no endpoint_type given but project id was found
                elif not endpoint_type and project_id != taxonomy.UNKNOWN:
                    break
        finally:
            if project_id == taxonomy.UNKNOWN:
                self.logger.debug("found no project id in endpoints for service type '{0}'".format(self.service_type))
            else:
                self.logger.debug("found target project id '{0}' in endpoints for service type '{1}'".format(project_id, self.service_type))
            return project_id

    def get_project_domain_and_user_id_from_keystone_authentication_request(self, req):
        """
        get project, domain, user id from authentication request.
        used in combination with client_addr to determine which client authenticates in which scope

        :param req: the request
        :return: project_id, domain_id, user_id
        """
        project_id = domain_id = user_id = taxonomy.UNKNOWN
        try:
            if not req.json:
                return

            json_body_dict = common.load_json_dict(req.json)
            if not json_body_dict:
                return
            project_id = common.find_project_id_in_auth_dict(json_body_dict)
            domain_id = common.find_domain_id_in_auth_dict(json_body_dict)
            user_id = common.find_user_id_in_auth_dict(json_body_dict)
        except Exception as e:
            self.logger.debug('unable to parse keystone authentication request body: {0}'.format(str(e)))
        finally:
            return project_id, domain_id, user_id

    def get_target_account_container_id_from_request(self, req):
        """
        get swift account id, container name from request

        :param req: the request
        :return: account uid, container name or unknown
        """
        # break here if we don't have the object-store strategy
        if self.strategy.name != 'object-store':
            return taxonomy.UNKNOWN, taxonomy.UNKNOWN

        account_id, container_id, _ = self.strategy.get_swift_account_container_object_id_from_path(req.path)
        return account_id, container_id

    def determine_target_type_uri(self, req):
        """
        determine the target type uri as per concrete strategy

        :param req: the request
        :return: the target type uri or taxonomy.UNKNOWN
        """
        target_type_uri = self.strategy.determine_target_type_uri(req)
        self.logger.debug("target type URI of requests '{0} {1}' is '{2}'"
                          .format(req.method, req.path, target_type_uri))
        return target_type_uri

    def determine_cadf_action(self, req, target_type_uri=None):
        """
        attempts to determine the cadf action for a request in the following order:
        (1) return custom action if one is configured
        (2) if /action, /os-instance-action request, return action from request body
        (3) return action based on request method

        :param custom_action_config: configuration of custom actions
        :param target_type_uri: the target type URI
        :param req: the request
        :return: the cadf action or unknown
        """
        cadf_action = self.strategy.determine_cadf_action(req, target_type_uri)
        self.logger.debug("cadf action for '{0} {1}' is '{2}'".format(req.method, req.path, cadf_action))
        return cadf_action


def load_config(config_path):
    yaml_conf = {}
    try:
        with open(config_path, 'r') as f:
            yaml_conf = yaml.safe_load(f)
    except Exception as e:
        raise errors.ConfigError("Failed to load configuration from file %s: %s" % (config_path, str(e)))
    finally:
        return yaml_conf
