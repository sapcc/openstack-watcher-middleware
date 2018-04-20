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

import os
import yaml

from oslo_log import log
from oslo_config import cfg
from datadog.dogstatsd import DogStatsd
from webob import Request

from .errors import ConfigError


class OpenStackWatcherMiddleware(object):
    """
    OpenStack Watcher Middleware

    Watcher and analyzes OpenStack traffic and maps to actions
    """

    statsd_prefix = "openstack_watcher"
    service = None

    def __init__(self, app, config_file, statsd_host="127.0.0.1", statsd_port="9125", logger=log.getLogger(__name__)):
        log.register_options(cfg.CONF)
        log.setup(cfg.CONF, "openstack_watcher_middleware")
        self.logger = logger
        self.app = app

        # statsd client
        self.metricsClient = DogStatsd(
            host=os.getenv('STATSD_HOST', statsd_host),
            port=int(os.getenv('STATSD_PORT', statsd_port)),
            namespace=os.getenv('STATSD_PREFIX', self.statsd_prefix)
        )

        self.config = load_and_check_config(config_file)

    @classmethod
    def factory(cls, global_config, **local_config):
        conf = global_config.copy()
        conf.update(local_config)

        def watcher(app):
            return OpenStackWatcherMiddleware(app, config_file=conf['config_file'])
        return watcher

    def __call__(self, environ, start_response):
        """
        WSGI entry point. Wraps environ in webob.Request

        :param environ: the WSGI environment dict
        :param start_response: WSGI callable
        """
        self.metricsClient.open_buffer()
        req = Request(environ)
        resp = self.app

        # TODO: anlayze request and pass on action keys to subsequent middleware in environ
        # TODO: prometheus metrics

        return resp(environ, start_response)


def load_and_check_config(cfg_file):
    """
    loads and checks configuration file

    :param cfg_file: path to the configuration file
    :return: the configuration
    """
    conf = {}

    if not os.path.exists(cfg_file):
        raise ConfigError('Configuration file %s not found' % cfg_file)

    try:
        with open(cfg_file, 'r') as f:
            parsed_conf = yaml.safe_load(f)

    except IOError as e:
        raise ConfigError("Failed to load configuration from file %s: %s" % (cfg_file, str(e)))

    finally:
        f.close()

    # TODO:

    return conf
