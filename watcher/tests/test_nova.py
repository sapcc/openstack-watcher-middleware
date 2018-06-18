import os
import unittest

import watcher.common as common
from watcher.watcher import load_config
from . import fake
from watcher.watcher import OpenStackWatcherMiddleware
from watcher import target_type_uri_strategy as ttus

WORKDIR = os.path.dirname(os.path.realpath(__file__))
NOVA_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/nova-complex.yaml'


class TestNova(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(fake.FakeApp(), {})
        self.watcher.service_type = 'compute'
        self.nova = ttus.NovaTargetTypeURIStrategy()
        self.is_setup = True

    def test_custom_action(self):
        raw_config = load_config(NOVA_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the nova complex config should not be None")

        stimuli = [
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"addFloatingIp": {"foo": "bar"}}
                ),
                'expected': 'update/addFloatingIp'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"removeSecurityGroup": {"name": "foobar"}}
                ),
                'expected': 'update/removeSecurityGroup'
            },
            {
                'request': fake.create_request(path='/v2.1/os-snapshots'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v2.1/os-snapshots', method='POST'),
                'expected': 'create'
            },
            {
                'request': fake.create_request(path='/v2.1/servers'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v2.1/servers/0123456789abcdef0123456789abcdef/ips'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v2.1/servers/0123456789abcdef0123456789abcdef/ips/label'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"os-getConsoleOutput": {"length": 50}}
                ),
                'expected': 'update/getConsoleOutput'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"os-getVNCConsole": {"type": "novnc"}}
                ),
                'expected': 'update/os-getVNCConsole'
            },
            {
                'request': fake.create_request(path='/v2.1/servers/0123456789abcdef0123456789abcdef/os-instance-actions'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/flavors/0123456789abcdef0123456789abcdef/os-extra_specs'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/flavors/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"addTenantAccess": {"tenant": "fakeTenant"}}
                ),
                'expected': 'update/addTenantAccess'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/images/0123456789abcdef0123456789abcdef/metadata'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/os-aggregates/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"add_host": {"host": "21549b2f665945baaa7101926a00143c"}},
                ),
                'expected': 'update/add_host'
            },
        ]

        for s in stimuli:
            req = s.get('request')
            expected = s.get('expected')
            target_type_uri = self.nova.determine_target_type_uri(req)
            self.assertIsNotNone(target_type_uri, "target.type_uri should not be None. request: {0}".format(req))
            self.assertIsNot(target_type_uri, 'unknown', "target.type_uri shoud not be 'unknown'. request: {0}".format(req))
            self.assertEqual(
                self.watcher.determine_cadf_action(config, target_type_uri, req),
                expected,
                "cadf action for '{0}' should be '{1}'".format(req, expected)
            )


if __name__ == '__main__':
    unittest.main()
