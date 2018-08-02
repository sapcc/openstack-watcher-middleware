import os
import unittest

from . import fake
from watcher.watcher import load_config
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
            }
        )
        self.is_setup = True

    def test_cadf_action(self):
        raw_config = load_config(IRONIC_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the ironic config should not be None")

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
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            target_type_uri = self.watcher.determine_target_type_uri(req)
            self.assertIsNotNone(target_type_uri, 'target.type_uri for req {0} must not be None'.format(req))
            self.assertIsNot(target_type_uri, 'unknown', "target.type_uri for req {0} must not be 'unknown'".format(req))

            actual = self.watcher.determine_cadf_action(config, target_type_uri, req)

            self.assertEqual(
                actual,
                expected,
                "cadf action for '{0} {1}' should be '{2}' but got '{3}'".format(req.method, target_type_uri, expected, actual)
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
            }
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
