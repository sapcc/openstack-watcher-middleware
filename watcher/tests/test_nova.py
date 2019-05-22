import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware

WORKDIR = os.path.dirname(os.path.realpath(__file__))
NOVA_CONFIG_PATH = WORKDIR + '/fixtures/nova-complex.yaml'


class TestNova(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'compute',
                'config_file': NOVA_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_custom_action(self):
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
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"os-getConsoleOutput": {"length": 50}}
                ),
                'expected': 'update/os-getConsoleOutput'
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
            actual = self.watcher.determine_cadf_action(req)

            self.assertEqual(
                actual,
                expected,
                "cadf action for '{0} {1}' should be '{2}' but got '{3}'".format(req.method, req.path, expected, actual)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': fake.create_request(
                    path='/servers/myserver'),
                'expected': 'service/compute/servers/server'
            },
            {
                'request': fake.create_request(
                    path='/servers/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/servers/server'
            },
            {
                'request': fake.create_request(
                    path='/flavors/myflavorname'),
                'expected': 'service/compute/flavors/flavor'
            },
            {
                'request': fake.create_request(
                    path='/flavors/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/flavors/flavor'
            },
            {
                'request': fake.create_request(
                    path='/flavors/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/flavors/flavor'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/os-aggregates/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"add_host": {"host": "21549b2f665945baaa7101926a00143c"}},
                ),
                'expected': 'service/compute/os-aggregates/os-aggregate/action'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/myservername/action',
                    method='POST',
                    body_dict={"os-getVNCConsole": {"type": "novnc"}}
                ),
                'expected': 'service/compute/servers/server/action'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    method='POST',
                    body_dict={"os-getVNCConsole": {"type": "novnc"}}
                ),
                'expected': 'service/compute/servers/server/action'
            },
            {
                'request': fake.create_request(
                    path='/servers/0123456789abcdef0123456789abcdef/metadata/0123456789abcdef0123456789abcdef'
                ),
                'expected': 'service/compute/servers/server/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/servers/myserver/metadata/foobar'
                ),
                'expected': 'service/compute/servers/server/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/os-availability-zone/detail'
                ),
                'expected': 'service/compute/os-availability-zone/detail'
            },
            {
                'request': fake.create_request(
                    path='/os-quota-sets/0123456789abcdef0123456789abcdef/defaults'
                ),
                'expected': 'service/compute/os-quota-sets/os-quota-set/defaults'
            },
            {
                'request': fake.create_request(
                    path='/os-networks/add'
                ),
                'expected': 'service/compute/os-networks/add'
            },
            {
                'request': fake.create_request(
                    path='/os-networks/0123456789abcdef0123456789abcdef'
                ),
                'expected': 'service/compute/os-networks/os-network'
            },
            {
                'request': fake.create_request(
                    path='/os-hypervisors/foobar/servers'
                ),
                'expected': 'service/compute/os-hypervisors/os-hypervisor/servers'
            },
            {
                'request': fake.create_request(
                    path='/os-certificates/root'
                ),
                'expected': 'service/compute/os-certificates/root'
            },
            {
                'request': fake.create_request(
                    path='/os-cloudpipe/configure-project'
                ),
                'expected': 'service/compute/os-cloudpipe/configure-project'
            },
            {
                'request': fake.create_request(
                    path='/v2.1'
                ),
                'expected': 'service/compute/versions'
            },
            {
                'request': fake.create_request(
                    path='/v2.0'
                ),
                'expected': 'service/compute/versions'
            },
            {
                'request': fake.create_request(
                    path='/'
                ),
                'expected': 'service/compute/root'
            },
            {
                'request': fake.create_request(
                    path=''
                ),
                'expected': 'service/compute/root'
            },
            {
                'request': fake.create_request(
                    path='/2009-04-04/meta-data/block-device-mapping'
                ),
                'expected': 'service/compute/version/meta-data/block-device-mapping'
            },
            {
                'request': fake.create_request(
                    path='/2009-04-04/meta-data/block-device-mapping/root'
                ),
                'expected': 'service/compute/version/meta-data/block-device-mapping/block-device-mapping'
            },
            {
                'request': fake.create_request(
                    path='/2012-01-12/meta-data'
                ),
                'expected': 'service/compute/version/meta-data'
            },
            {
                'request': fake.create_request(
                    path='/2012-01-12/meta-data/hostname'
                ),
                'expected': 'service/compute/version/meta-data/hostname'
            },
            {
                'request': fake.create_request(
                    path='/2012-01-12'
                ),
                'expected': 'service/compute/version'
            },
            {
                'request': fake.create_request(
                    path='/latest/meta-data'
                ),
                'expected': 'service/compute/version/meta-data'
            }
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            actual = self.watcher.determine_target_type_uri(req)

            self.assertEqual(
                actual,
                expected,
                "target_type_uri of '{0} {1}' should be '{2}' but got '{3}'".format(req.method, req.path, expected, actual)
            )


if __name__ == '__main__':
    unittest.main()
