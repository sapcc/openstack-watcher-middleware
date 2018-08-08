import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
MANILA_CONFIG_PATH = WORKDIR + '/fixtures/manila.yaml'


class TestManila(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'share',
                'config_file': MANILA_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_cadf_action(self):

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
                'expected': 'foobar'
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
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict='{ "access_list": null }'
                ),
                'expected': 'update/access_list'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict=u'{ "access_list": null }'
                ),
                'expected': 'update/access_list'
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
                    path='/v2/b206a1900310484f8a9504754c84b067/extensions'),
                'expected': 'service/storage/share/extensions'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/limits'),
                'expected': 'service/storage/share/limits'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares'),
                'expected': 'service/storage/share/shares'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/detail'),
                'expected': 'service/storage/share/shares/detail'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/shares/share'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/export_locations/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/shares/share/export_locations/export_location'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/hasse/export_locations/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/shares/share/export_locations/export_location'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/metadata/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/share/shares/share/metadata/key'
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
                'expected': 'service/storage/share/shares/share/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/hase/action',
                    body_dict={
                        "allow_access": {
                            "access_level": "rw",
                            "access_type": "ip",
                            "access_to": "0.0.0.0/0"
                        }
                    }
                ),
                'expected': 'service/storage/share/shares/share/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'service/storage/share/shares/share/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    body_dict={
                        "unmanage": "null"
                    }
                ),
                'expected': 'service/storage/share/snapshots/snapshot/action'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/os-share-unmanage/b206a1900310484f8a9504754c84b067/unmanage'
                ),
                'expected': 'service/storage/share/os-share-unmanage/share/unmanage'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/share-group-types/foobar'
                ),
                'expected': 'service/storage/share/share-group-types/share-group-type'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/shares/manage'
                ),
                'expected': 'service/storage/share/shares/manage'
            },
            {
                'request': fake.create_request(
                    path='/v2/b206a1900310484f8a9504754c84b067/scheduler-stats/pools'
                ),
                'expected': 'service/storage/share/scheduler-stats/pools'
            },
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
