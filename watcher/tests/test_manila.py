import os
import unittest

from . import fake
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
MANILA_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/manila.yaml'


class TestCinder(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'share',
            }
        )
        self.is_setup = True

    def test_cadf_action(self):
        raw_config = load_config(MANILA_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the manila config should not be None")

        stimuli = [
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/extensions'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/limits'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/detail'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/export_locations'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "allow_access": {
                            "access_level": "rw",
                            "access_type": "ip",
                            "access_to": "0.0.0.0/0"
                        }
                    }
                ),
                'expected': 'update/allow_access'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'update/unmanage'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'update/unmanage'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            target_type_uri = self.watcher.determine_target_type_uri(req)
            self.assertIsNotNone(target_type_uri, 'target.type_uri for req {0} must not be None'.format(req))
            self.assertIsNot(target_type_uri, 'unknown', "target.type_uri for req {0} must not be 'unknown'".format(req))

            self.assertEqual(
                self.watcher.determine_cadf_action(config, target_type_uri, req),
                expected,
                "cadf action for '{0} {1}' should be '{2}'".format(req.method, target_type_uri, expected)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/extensions'),
                'expected': 'service/storage/share/tenant/extensions'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/limits'),
                'expected': 'service/storage/share/tenant/limits'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares'),
                'expected': 'service/storage/share/tenant/shares'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/detail'),
                'expected': 'service/storage/share/tenant/shares/detail'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/tenant/shares/share'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/export_locations/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/tenant/shares/share/export_locations/export_location'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/metadata/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/tenant/shares/share/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "allow_access": {
                            "access_level": "rw",
                            "access_type": "ip",
                            "access_to": "0.0.0.0/0"
                        }
                    }
                ),
                'expected': 'service/storage/share/tenant/shares/share/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'service/storage/share/tenant/shares/share/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'service/storage/share/tenant/snapshots/snapshot/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/os-share-unmanage/b206a1900310484f8a9504754c84b067/unmanage'
                ),
                'expected': 'service/storage/share/tenant/os-share-unmanage/share/unmanage'
            }
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            self.assertEqual(
                self.watcher.determine_target_type_uri(req),
                expected,
                "target_type_uri of '{0}' should be '{1}'".format(req, expected)
            )


if __name__ == '__main__':
    unittest.main()
