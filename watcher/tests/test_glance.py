import os
import unittest

import watcher.common as common
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware

from . import fake


WORKDIR = os.path.dirname(os.path.realpath(__file__))
GLANCE_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/glance.yaml'


class TestGlance(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'image'
            }
        )
        self.is_setup = True

    def test_custom_action(self):
        raw_config = load_config(GLANCE_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the glance config should not be None")

        stimuli = [
            {
                'target_type_uri': 'service/storage/image/images',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/storage/image/shared-images/member',
                'expected': 'read/list'
            },
            {
                'target_type_uri': 'service/storage/image/images/image/members',
                'method': 'POST',
                'expected': 'update'
            }
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

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': fake.create_request(path='/v3/images/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/image/images/image'
            },
            {
                'request': fake.create_request(path='/v3/images/ubuntu16.04'),
                'expected': 'service/storage/image/images/image'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            actual = self.watcher.determine_target_type_uri(req)
            self.assertEqual(
                actual,
                expected,
                "target_type_uri of '{0} {1}' should be '{2}' but got '{3}'"
                .format(req.method, req.path, expected, actual)
            )

if __name__ == '__main__':
    unittest.main()
