import os
import unittest

import watcher.common as common
from watcher.watcher import OpenStackWatcherMiddleware

from . import fake


WORKDIR = os.path.dirname(os.path.realpath(__file__))
GLANCE_CONFIG_PATH = WORKDIR + '/fixtures/glance.yaml'


class TestGlance(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'image',
                'config_file': GLANCE_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_custom_action(self):
        stimuli = [
            {
                'request': fake.create_request(
                    path="/v3/images/b206a1900310484f8a9504754c84b067"
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path="/v3/images/ubuntu16.04"
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path="/v3/images"
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path="/v2/images/myimage/actions/deactivate",
                    method='POST'
                ),
                'expected': 'create'
            },
            {
                'request': fake.create_request(
                    path="/v2/images/foobuntu/members"
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path="/v2/images/foobuntu/tags/bm",
                    method='DELETE'
                ),
                'expected': 'delete'
            },
            {
                'request': fake.create_request(
                    path="/v2/schemas/images"
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path="/v2/images/ubuntu10.10/file"
                ),
                'expected': 'read'
            }
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
                'request': fake.create_request(path='/v2/tasks'),
                'expected': 'service/storage/image/tasks'
            },
            {
                'request': fake.create_request(path='/v2/schemas/tasks'),
                'expected': 'service/storage/image/schemas/tasks'
            },
            {
                'request': fake.create_request(path='/v2/schemas/task'),
                'expected': 'service/storage/image/schemas/task'
            },
            {
                'request': fake.create_request(path='/v2/images/ubuntu16.04/actions/deactivate'),
                'expected': 'service/storage/image/images/image/actions/deactivate'
            },
            {
                'request': fake.create_request(path='/v2/images/coreos/actions/reactivate'),
                'expected': 'service/storage/image/images/image/actions/reactivate'
            },
            {
                'request': fake.create_request(path='/v3/images/ubuntu16.04'),
                'expected': 'service/storage/image/images/image'
            },
            {
                'request': fake.create_request(path='/v2/images/hase/members/myself'),
                'expected': 'service/storage/image/images/image/members/member'
            },
            {
                'request': fake.create_request(path='/v2/images/debian/tags/virtual'),
                'expected': 'service/storage/image/images/image/tags/tag'
            },
            {
                'request': fake.create_request(path='/v2/schemas/members'),
                'expected': 'service/storage/image/schemas/members'
            },
            {
                'request': fake.create_request(path='/v2/schemas/member'),
                'expected': 'service/storage/image/schemas/member'
            },
            {
                'request': fake.create_request(path='/v2/images/alpine/file'),
                'expected': 'service/storage/image/images/image/file'
            },
            {
                'request': fake.create_request(path='/v2/images/macos/stage'),
                'expected': 'service/storage/image/images/image/stage'
            },
            {
                'request': fake.create_request(path='/v2/info/import'),
                'expected': 'service/storage/image/info/import'
            },
            {
                'request': fake.create_request(path='/v2/info/stores'),
                'expected': 'service/storage/image/info/stores'
            },
            {
                'request': fake.create_request(path='/v2/tasks/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/image/tasks/task'
            },
            {
                'request': fake.create_request(path='/v2/schemas/tasks'),
                'expected': 'service/storage/image/schemas/tasks'
            }
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
