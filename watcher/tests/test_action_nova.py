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
        self.nova = ttus.NovaTargetTypeURIStrategy()
        self.is_setup = True

    def test_custom_action_simple(self):
        config = {
           'servers': [
                {'detail': 'read/list'},
                {'action':[
                    {'addFloatingIp': 'update/addFloatingIp'},
                    {'removeFloatingIp': 'update/removeFloatingIp'},
                ]}
            ],
           'flavors': [
                {'detail': 'read/list'},
                {'action': [
                    {'addTenantAccess': 'add/project-access'},
                    {'removeTenantAccess': 'remove/project-access'}
                ]}
            ]
        }

        stimuli = [
            {
                'target_type_uri': 'service/compute/servers/server/action/addFloatingIp',
                'expected': 'update/addFloatingIp',
                'help': "the custom action of 'POST compute/servers/action/addFloatingIp' should be 'update/addFloatingIp'"
            },
            {
                'target_type_uri': 'service/compute/servers/detail',
                'expected': 'read/list',
                'help': "the custom action of 'GET compute/servers/detail' should be 'read/list'"
            },
            {
                'target_type_uri': 'service/compute/flavors/action/addTenantAccess',
                'expected': 'add/project-access',
                'help': "the custom action of 'POST compute/flavors/flavor/action/addTenantAccess' should be 'add/project-access'"
            },
            {
                'target_type_uri': 'service/compute/flavors/action/removeTenantAccess',
                'expected': 'remove/project-access',
                'help': "the custom action of 'POST compute/flavors/flavor/action/removeTenantAccess' should be 'remove/project-access'"
            }
        ]

        for s in stimuli:
            self.assertEqual(
                common.determine_custom_cadf_action(config, s.get('target_type_uri')),
                s.get('expected'),
                s.get('help')
            )

    def test_determine_action(self):
        self.assertEqual(
            common.determine_cadf_action('GET', '/v2.0/servers/detail'),
            'read/list',
            "the action for 'GET /v2.0/servers/' should be 'read/list'"
        )

    def test_custom_action_complex(self):
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
            self.assertEqual(
                self.watcher.determine_cadf_action(config, target_type_uri, req),
                expected,
                "cadf action for '{0}' should be '{1}'".format(req, expected)
            )


if __name__ == '__main__':
    unittest.main()
