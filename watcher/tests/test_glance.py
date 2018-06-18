import os
import unittest

import watcher.common as common
from watcher.watcher import load_config


WORKDIR = os.path.dirname(os.path.realpath(__file__))
GLANCE_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/glance.yaml'


class TestGlance(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
