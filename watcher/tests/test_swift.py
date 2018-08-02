import os
import six
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
SWIFT_CONFIG_PATH = WORKDIR + '/fixtures/swift.yaml'


class TestSwift(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'object-store',
                'config_file': SWIFT_CONFIG_PATH,
                'project_id_from_path': 'true'
             }
        )
        self.is_setup = True

    def test_prefix(self):
        expected = 'service/storage/object'
        actual = self.watcher.strategy.target_type_uri_prefix

        self.assertEqual(
            actual,
            expected,
            "service type is object-store, hence the prefix should be '{0}' but got '{1}'".format(expected, actual)
        )

    def test_get_target_project_uid_from_path(self):
        self.assertEqual(
            self.watcher.get_target_project_uid_from_path('/v1/AUTH_b206a1900310484f8a9504754c84b067/containername/testfile'),
            'b206a1900310484f8a9504754c84b067',
            "project id in path '/v1/AUTH_b206a1900310484f8a9504754c84b067/containername/testfile' is be 'b206a1900310484f8a9504754c84b067'"
        )

    def test_cadf_action(self):
        stimuli = [
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername/testfile'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername/testfile',
                    method='HEAD'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername/testfile',
                    method='COPY'
                ),
                'expected': 'create/copy'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername/testfile',
                    method='PUT'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername/testfile',
                    method='POST'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789',
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername',
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789',
                    method='HEAD'

                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path="/v1/endpoints"),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789',
                    method='POST'
                ),
                'expected': 'update'
            }
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
                    path='/v1/AUTH_0123456789/containername/testfile'
                ),
                'expected': 'service/storage/object/account/container/object'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_foobar/containername/testfile'
                ),
                'expected': 'service/storage/object/account/container/object'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789/containername'
                ),
                'expected': 'service/storage/object/account/container'
            },
            {
                'request': fake.create_request(
                    path='/v1/AUTH_0123456789'
                ),
                'expected': 'service/storage/object/account'
            },
            {
                'request': fake.create_request(
                    path='/v1'
                ),
                'expected': 'service/storage/object/versions'
            },
            {
                'request': fake.create_request(
                    path='/v1/endpoints'
                ),
                'expected': 'service/storage/object/endpoints'
            },
            {
                'request': fake.create_request(
                    path='/info'
                ),
                'expected': 'service/storage/object/info'
            },
            {
                'request': fake.create_request(
                    path='/'
                ),
                'expected': 'service/storage/object/root'
            },
            {
                'request': fake.create_request(
                    path=''
                ),
                'expected': 'service/storage/object/root'
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

    def test_get_swift_project_id_from_path(self):
        stimuli = [
            {
                'path': '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132',
                'expected': 'e9141fb24eee4b3e9f25ae69cda31132',
                'help': "path '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132' contains the project id 'e9141fb24eee4b3e9f25ae69cda31132'"
            },
            {
                'path': '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132/container',
                'expected': 'e9141fb24eee4b3e9f25ae69cda31132',
                'help': "path '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132/container' contains the project id 'e9141fb24eee4b3e9f25ae69cda31132'"
            },
            {
                'path': '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132/container/object',
                'expected': 'e9141fb24eee4b3e9f25ae69cda31132',
                'help': "path '/v1/AUTH_e9141fb24eee4b3e9f25ae69cda31132/container/object' contains the project id 'e9141fb24eee4b3e9f25ae69cda31132'"
            },
            {
                'path': 'v1/foo/bar',
                'expected': 'unknown',
                'help': "'v1/foo/bar' does not contain a swift project id"
            }
        ]

        for stim in stimuli:
            self.assertEqual(
                self.watcher.strategy.get_swift_project_id_from_path(stim.get('path')),
                stim.get('expected'),
                stim.get('help')
            )

    def test_get_account_uid_and_container_name_from_request(self):
        stimuli = {
            '/v1/AUTH_0123456789/containername/testfile': ('0123456789', 'containername'),
        }

        for stim, expected in six.iteritems(stimuli):
            req = fake.create_request(
                path=stim,
                method='PUT'
            )

            self.assertEqual(
                self.watcher.get_target_account_container_id_from_request(req),
                expected
            )


if __name__ == '__main__':
    unittest.main()
