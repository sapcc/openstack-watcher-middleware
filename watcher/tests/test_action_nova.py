import os
import unittest

import watcher.common as common
from watcher.watcher import load_config


WORKDIR = os.path.dirname(os.path.realpath(__file__))
NOVA_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/nova-complex.yaml'


class TestNova(unittest.TestCase):
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
                'target_type_uri': 'service/compute/servers/server/action',
                'method': 'POST',
                'os_action': 'addFloatingIp',
                'expected': 'update/addFloatingIp'
            },
            {
                'target_type_uri': 'service/compute/servers/server/action',
                'method': 'POST',
                'os_action': 'removeSecurityGroup',
                'expected': 'update/removeSecurityGroup'
            },
            {
                'target_type_uri': 'service/compute/os-snapshots',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/os-snapshots',
                'method': 'POST',
                'expected': 'unknown'
            },
            {
                'target_type_uri': 'service/compute/servers',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/servers/server/ips',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/servers/server/ips/label',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/servers/server/action',
                'os_action': 'os-getConsoleOutput',
                'expected': 'update/os-getConsoleOutput'
            },
            {
                'target_type_uri': 'service/compute/servers/os-instance-actions',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/flavors/flavor/os-extra_specs',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/flavors/flavor/action',
                'method': 'POST',
                'os_action': 'addTenantAccess',
                'expected': 'update/addTenantAccess'
            },
            {
                'target_type_uri': 'service/compute/images/image/metadata',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/compute/os-aggregates/os-aggregate/action',
                'method': 'POST',
                'os_action': 'add_host',
                'expected': 'update/add_host'
            },
        ]

        for s in stimuli:
            target_type_uri = s.get('target_type_uri')
            method = s.get('method', 'GET')
            os_action = s.get('os_action')
            expected = s.get('expected')
            self.assertEqual(
                common.determine_custom_cadf_action( config,target_type_uri, method, os_action,),
                expected,
                "cadf action for '{0} {1} {2}' should be '{3}'".format(method, target_type_uri, os_action, expected)
            )


if __name__ == '__main__':
    unittest.main()
