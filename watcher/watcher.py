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
import json
import yaml
import time

from datadog.dogstatsd import DogStatsd
from pycadf import cadftaxonomy as taxonomy
from webob import Request

from . import common
from . import errors
from . import target_type_uri_strategy as ttu

logging.basicConfig(level=logging.ERROR, format='%(asctime)-15s %(message)s')

STRATEGIES = {
    'object-store': ttu.SwiftTargetTypeURIStrategy,
    'compute': ttu.NovaTargetTypeURIStrategy,
    'image': ttu.GlanceTargetTypeURIStrategy,
    'volume': ttu.CinderTargetTypeURIStrategy,
    'network': ttu.NeutronTargetTypeURIStrategy,
    'dns': ttu.DesignateTargetTypeURIStrategy,
    'identity': ttu.KeystoneTargetTypeURIStrategy,
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
        self.is_project_id_from_path = common.string_to_bool(self.wsgi_config.get('target_project_id_from_path', 'False'))
        self.is_project_id_from_service_catalog = common.string_to_bool(
            self.wsgi_config.get('target_project_id_from_service_catalog', 'False'))
        self.prefix = self.cadf_service_name or 'service/{0}'.format(self.service_type)

        config_file_path = config.get('config_file', None)
        if config_file_path:
            try:
                self.watcher_config = load_config(config_file_path)
            except errors.ConfigError as e:
                self.logger.warning("custom actions not available: %s", str(e))

        self.custom_action_config = self.watcher_config.get('custom_actions', {})

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

        # determine initiator based on token
        initiator_project_id, initiator_domain_id, initiator_user_id = \
            self.get_initiator_project_domain_user_uid_from_environ(req, environ)
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
        cadf_action = self.determine_cadf_action(self.custom_action_config, target_type_uri, req)

        # initiator
        environ['WATCHER.INITIATOR_PROJECT_ID'] = initiator_project_id
        environ['WATCHER.INITIATOR_DOMAIN_ID'] = initiator_domain_id
        environ['WATCHER.INITIATOR_USER_ID'] = initiator_user_id
        environ['WATCHER.INITIATOR_HOST_ADDRESS'] = initiator_host_address

        # target
        environ['WATCHER.TARGET_PROJECT_ID'] = target_project_id
        environ['WATCHER.TARGET_TYPE_URI'] = target_type_uri
        environ['WATCHER.ACTION'] = cadf_action
        environ['WATCHER.SERVICE_TYPE'] = self.service_type

        labels = [
            "service:{0}".format(self.service_type),
            "action:{0}".format(cadf_action),
            "initiator_project_id:{0}".format(initiator_project_id),
            "initiator_domain_id:{0}".format(initiator_domain_id),
            "target_project_id:{0}".format(target_project_id),
            "target_type_uri:{0}".format(target_type_uri),
        ]

        # if swift request: determine target.container_id based on request path
        if common.is_swift_request(req.path) or self.service_type == 'object-store':
            _, target_container_id = self.get_target_account_container_id_from_request(req)
            environ['WATCHER.TARGET_CONTAINER_ID'] = target_container_id

        self.logger.debug(
            'got request with initiator_project_id: {0}, initiator_domain_id: {1}, initiator_user_id: {2}, '
            'target_project_id: {3}, action: {4}, target_type_uri: {5}'
            .format(initiator_project_id, initiator_domain_id, initiator_user_id,
                    target_project_id, cadf_action, target_type_uri
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

                self.metric_client.timing('api_requests_duration_seconds', time.time() - start, tags=labels)
                self.metric_client.increment('api_requests_total', tags=labels)
            except Exception as e:
                self.logger.info("failed to submit metrics for %s: %s" % (str(labels), str(e)))
            finally:
                self.metric_client.close_buffer()

    def get_initiator_project_domain_user_uid_from_environ(self, req, environ):
        """
        get the project uid, domain uid, user uid from the environ
        as parsed by the keystone.auth_token middleware

        :param environ: the request's environ
        :return: project, domain, user uid
        """
        project_id = environ.get('HTTP_X_PROJECT_ID', taxonomy.UNKNOWN)
        domain_id = environ.get('HTTP_X_DOMAIN_ID', taxonomy.UNKNOWN)
        user_id = environ.get('HTTP_X_USER_ID', taxonomy.UNKNOWN)
        if not (project_id or domain_id):
            project_id, domain_id, user_id = self.get_project_domain_and_user_id_from_keystone_authentications_request(req)
        return project_id, domain_id, user_id

    def get_target_project_uid_from_path(self, path):
        """
        get the project uid from the path, which should look like
        ../v1.2/<project_uid>/.. or ../v1/AUTH_<project_uid>/..

        :param path: the request path containing a project uid
        :return: the project uid
        """
        project_uid = taxonomy.UNKNOWN
        try:
            if common.is_swift_request(path):
                project_uid = common.get_swift_project_id_from_path(path)
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

                if self.service_type == 'object-store':
                    project_id = common.get_swift_project_id_from_path(url)
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

    def get_target_project_domain_and_user_id_from_keystone_authentications_request(self, req):
        """
        get project, domain, user id from authentication request.
        used in combination with client_addr to determine which client authenticates in which scope

        :param req: the request
        :return: project_id, domain_id, user_id
        """
        project_id = domain_id = user_id = taxonomy.UNKNOWN
        try:
            json_body_dict = json.loads(req.json_body)
            if not json_body_dict:
                return taxonomy.UNKNOWN
            project_id = common.find_project_id_in_auth_dict(json_body_dict)
            domain_id = common.find_domain_id_in_auth_dict(json_body_dict)
            user_id = common.find_user_id_in_auth_dict(json_body_dict)
        except ValueError as e:
            self.logger.warning('unable to read request body: ', str(e))
        finally:
            return project_id, domain_id, user_id

    def get_target_account_container_id_from_request(self, req):
        """
        get swift account id, container name from request

        :param req: the request
        :return: account uid, container name or unknown
        """
        account_id, container_id, _ = common.get_swift_account_container_object_id_from_path(req.path)
        return account_id, container_id

    def determine_target_type_uri(self, req):
        """
        determine the target type uri as per concrete strategy

        :param req: the request
        :return: the target type uri or taxonomy.UNKNOWN
        """
        strat = STRATEGIES.get(
            self.service_type,
            ttu.TargetTypeURIStrategy
        )
        strategy = strat()
        strategy.name = self.service_type
        strategy.logger = self.logger

        if self.prefix and not strategy.prefix:
            strategy.prefix = self.prefix

        self.logger.debug("selected strategy '{0}' to determine target.type_uri".format(strategy.name))
        return strategy.determine_target_type_uri(req)

    def determine_cadf_action(self, custom_action_config, target_type_uri, req):
        """
        attempts to determine the cadf action for a request in the following order:
        (1) return custom action if one is configured
        (2) if /action, /os-instance-action request, return action from request body
        (3) return action based on request method

        :param custom_action_config: configuration of custom actions
        :param target_type_uri: the target.type_uri
        :param req: the request
        :return: the cadf action or unknown
        """
        # determine action as per custom action configuration
        cadf_action = taxonomy.UNKNOWN
        os_action = None
        try:
            if common.is_action_request(req):
                os_action = common.determine_openstack_action_from_request(req)

            # search custom action configuration
            cadf_action = common.determine_custom_cadf_action(
                config=custom_action_config,
                target_type_uri=target_type_uri,
                method=req.method,
                os_action=os_action,
                prefix=self.prefix
            )
            self.logger.debug("custom action for {0} {1}: {2},".format(req.method, req.path, cadf_action))

            # if action request and cadf action still unknown, attempt to convert from os-action
            if os_action and cadf_action == taxonomy.UNKNOWN:
                cadf_action = common.openstack_action_to_cadf_action(os_action)

            # if still unknown, determine cadf action based on HTTP method (and path for authentication req)
            if cadf_action == taxonomy.UNKNOWN:
                cadf_action = common.determine_cadf_action_from_request(req)

        except Exception as e:
            self.logger.warning('unable to determine cadf action: {}'.format(str(e)))

        finally:
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
