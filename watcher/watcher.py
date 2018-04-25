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

import json
import yaml

from datadog.dogstatsd import DogStatsd
from oslo_log import log
from oslo_config import cfg
from pycadf import cadftaxonomy as taxonomy
from webob import Request

from . import common
from . import errors
from . import target_type_uri_strategy as ttu


class OpenStackWatcherMiddleware(object):
    """
    OpenStack Watcher Middleware

    Watches OpenStack traffic and classifies according to CADF standard
    """
    def __init__(self, app, config, logger=log.getLogger(__name__)):
        log.register_options(cfg.CONF)
        log.setup(cfg.CONF, "openstack_watcher_middleware")
        self.logger = logger
        self.app = app
        self.wsgi_config = config
        self.watcher_config = {}
        self.service_name = config.get("service_name", taxonomy.UNKNOWN)
        self.service_type = config.get('keystone_service_type', None)
        # prefix for target_type_uri
        self.prefix = self.wsgi_config.get('service_prefix', 'service/{0}/'.format(self.service_name))
        # get the project uid from the request path or from the token (default)
        self.is_project_id_from_path = common.string_to_bool(self.wsgi_config.get('project_id_from_path', 'False'))
        self.is_project_id_from_service_catalog = common.string_to_bool(
            self.wsgi_config.get('project_id_from_service_catalog', 'False'))

        config_file_path = config.get('config_file', None)
        if config_file_path:
            try:
                self.watcher_config = load_config(config_file_path)
            except errors.ConfigError as e:
                self.logger.warning("Custom actions not available: %s", str(e))

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
        req = Request(environ)

        # determine initiator based on token
        initiator_project_id, initiator_domain_id, initiator_user_id = \
            self.get_initiator_project_domain_user_uid_from_environ(req, environ)
        initiator_client_addr = req.client_addr or taxonomy.UNKNOWN

        # determine target based on request path or keystone.token_info
        target_project_id = taxonomy.UNKNOWN
        if self.is_project_id_from_path:
            target_project_id = self.get_target_project_uid_from_path(req.path)
        elif self.is_project_id_from_service_catalog:
            target_project_id = self.get_target_project_id_from_keystone_token_info(environ.get('keystone.token_info'))

        # determine target accound, container id based on request path
        target_account_id = target_container_id = taxonomy.UNKNOWN
        if common.is_swift_request(req.path):
            target_account_id, target_container_id = self.get_target_account_container_id_from_request(req)

        target_type_uri = self.determine_target_type_uri(req)

        action = taxonomy.UNKNOWN
        # determine action as per custom action configuration
        custom_action_config = self.watcher_config.get('custom_actions', {})
        if custom_action_config:
            action = common.determine_custom_action(
                config=custom_action_config,
                target_type_uri=target_type_uri,
                method=req.method,
                prefix=self.prefix
            )
            self.logger.debug("custom action for {0} {1}: {2},".format(req.method, req.path, action))
        if not action or action == taxonomy.UNKNOWN:
            # determine action based on HTTP method (and path for authentication req)
            action = common.determine_action_from_request(req)

        # initiator
        environ['WATCHER.INITIATOR_PROJECT_ID'] = initiator_project_id
        environ['WATCHER.INITIATOR_DOMAIN_ID'] = initiator_domain_id
        environ['WATCHER.INITIATOR_USER_ID'] = initiator_user_id
        environ['WATCHER.INITIATOR_CLIENT_ADDR'] = initiator_client_addr

        # target
        environ['WATCHER.TARGET_PROJECT_ID'] = target_project_id
        environ['WATCHER.TARGET_ACCOUNT_ID'] = target_account_id
        environ['WATCHER.TARGET_CONTAINER_ID'] = target_container_id
        environ['WATCHER.TARGET_TYPE_URI'] = target_type_uri
        environ['WATCHER.ACTION'] = action
        environ['WATCHER.SERVICE_NAME'] = self.service_name

        self.logger.debug(
            'got request with initiator_project_id: {0}, initiator_domain_id: {1}, initiator_user_id: {2}, '
            'target_project_id: {3}, target_account_id: {4}, target_container_id: {5}, '
            'action: {6}, target_type_uri: {7}'
            .format(initiator_project_id, initiator_domain_id, initiator_user_id,
                    target_project_id, target_account_id, target_container_id,
                    action, target_type_uri
                    )
        )

        labels = [
            "service:{0}".format(self.service_name),
            "action:{0}".format(action),
            "initiator_project_id:{0}".format(initiator_project_id),
            "initiator_domain_id:{0}".format(initiator_domain_id),
            "target_project_id:{0}".format(target_project_id),
            "target_type_uri:{0}".format(target_type_uri),
        ]
        try:
            self.metric_client.open_buffer()

            self.metric_client.increment(
                "api_requests_total",
                tags=labels,
            )

        except Exception as e:
            self.logger.info("failed to submit metrics for %s: %s" % (str(labels), str(e)))

        finally:
            self.metric_client.close_buffer()
            return self.app(environ, start_response)

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
                project_uid = common.get_swift_project_id(path)
            else:
                project_uid = common.get_project_id_from_os_path()
        finally:
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
            self.logger.debug('unable to get project id from service catalog: ', str(e))
        finally:
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
        if common.is_swift_request(req.path):
            swift_strategy = ttu.SwiftTargetTypeURIStrategy(prefix=self.prefix)
            return swift_strategy.determine_target_type_uri(req)
        generic_strategy = ttu.GenericTargetTypeURIStrategy(prefix=self.prefix)
        return generic_strategy.determine_target_type_uri(req)


def load_config(config_path):
    yaml_conf = {}
    try:
        with open(config_path, 'r') as f:
            yaml_conf = yaml.safe_load(f)
    except Exception as e:
        raise errors.ConfigError("Failed to load configuration from file %s: %s" % (config_path, str(e)))
    finally:
        f.close()
        return yaml_conf
