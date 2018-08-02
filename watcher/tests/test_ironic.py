import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
IRONIC_CONFIG_PATH = WORKDIR + '/fixtures/ironic.yaml'


class TestIronic(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'baremetal',
                'config_file': IRONIC_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_cadf_action(self):
        stimuli = [
            {
                'request': fake.create_request(path='/v1/nodes'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/vendor_passthru'),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/vendor_passthru/methods'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/bios'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/portgroups/myportgroup/ports'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/drivers/mydriver/vendor_passthru/methods'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynode/states'),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path='/v1/chassis'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/chassis/mainchassis'),
                'expected': 'read'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
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
                    path='/v1/nodes'),
                'expected': 'service/compute/baremetal/nodes'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynodename'),
                'expected': 'service/compute/baremetal/nodes/node'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/compute/baremetal/nodes/node'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynode/maintenance'),
                'expected': 'service/compute/baremetal/nodes/node/maintenance'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/b206a1900310484f8a9504754c84b067/maintenance'),
                'expected': 'service/compute/baremetal/nodes/node/maintenance'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynodename/traits/mytraitname'),
                'expected': 'service/compute/baremetal/nodes/node/traits/trait'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/b206a1900310484f8a9504754c84b067/traits/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/compute/baremetal/nodes/node/traits/trait'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/b206a1900310484f8a9504754c84b067/vifs/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/compute/baremetal/nodes/node/vifs/vif'
            },
            {
                'request': fake.create_request(
                    path='/v1/drivers/gooddriver/raid/logical_disk_properties'),
                'expected': 'service/compute/baremetal/drivers/driver/raid/logical_disk_properties'
            },
            {
              'request': fake.create_request(
                  path='/v1/nodes/hase/bios/biossettingname'),
              'expected': 'service/compute/baremetal/nodes/node/bios/setting'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynnode/management/boot_device/supported'),
                'expected': 'service/compute/baremetal/nodes/node/management/boot_device/supported'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynode/states/raid'),
                'expected': 'service/compute/baremetal/nodes/node/states/raid'
            },
            {
                'request': fake.create_request(
                    path='/v1/nodes/mynode/states'),
                'expected': 'service/compute/baremetal/nodes/node/states'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/vendor_passthru/methods'),
                'expected': 'service/compute/baremetal/nodes/node/vendor_passthru/methods'
            },
            {
                'request': fake.create_request(path='/v1/nodes/foobar/portgroups/detail'),
                'expected': 'service/compute/baremetal/nodes/node/portgroups/detail'
            },
            {
                'request': fake.create_request(path='/v1/volume/connectors/myconnector'),
                'expected': 'service/compute/baremetal/volume/connectors/connector'
            },
            {
                'request': fake.create_request(path='/v1/portgroups/someportgroup/ports/detail'),
                'expected': 'service/compute/baremetal/portgroups/portgroup/ports/detail'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/volume/connectors'),
                'expected': 'service/compute/baremetal/nodes/node/volume/connectors'
            },
            {
                'request': fake.create_request(path='/v1/nodes/mynode/volume/targets'),
                'expected': 'service/compute/baremetal/nodes/node/volume/targets'
            },
            {
                'request': fake.create_request(path='/v1/chassis/mainchassis'),
                'expected': 'service/compute/baremetal/chassis/chassis'
            },
            {
                'request': fake.create_request(path='/v1/chassis/detail'),
                'expected': 'service/compute/baremetal/chassis/detail'
            },
            {
                'request': fake.create_request(path='/v1/heartbeat/dev-instance-00'),
                'expected': 'service/compute/baremetal/heartbeat/node'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            actual = self.watcher.determine_target_type_uri(req)

            self.assertEqual(
                actual,
                expected,
                "target_type_uri of '{0}' should be '{1}' but got '{2}'".format(req, expected, actual)
            )


if __name__ == '__main__':
    unittest.main()
