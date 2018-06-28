import os
import unittest

from webob import Request

from . import fake
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
SWIFT_CONFIG_PATH = WORKDIR + '/fixtures/swift.yaml'


class TestDesignate(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'object-store',
                'cadf_service_name': 'service/storage/object',
                'project_id_from_path': 'true'
             }
        )
        self.is_setup = True

    def test_get_target_project_uid_from_path(self):
        self.assertEqual(
            self.watcher.get_target_project_uid_from_path('/v1/AUTH_b206a1900310484f8a9504754c84b067/containername/testfile'),
            'b206a1900310484f8a9504754c84b067',
            "project id in path '/v1/AUTH_b206a1900310484f8a9504754c84b067/containername/testfile' is be 'b206a1900310484f8a9504754c84b067'"
        )

    def test_cadf_action(self):
        raw_config = load_config(SWIFT_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the swift config should not be None")

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
                    path='/v1/AUTH_0123456789',
                    method='HEAD'

                ),
                'expected': 'read'
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
            target_type_uri = self.watcher.determine_target_type_uri(req)
            self.assertIsNotNone(target_type_uri, 'target.type_uri for req {0} must not be None'.format(req))
            self.assertIsNot(target_type_uri, 'unknown',
                             "target.type_uri for req {0} must not be 'unknown'".format(req))

            self.assertEqual(
                self.watcher.determine_cadf_action(config, target_type_uri, req),
                expected,
                "cadf action for '{0} {1}' should be '{2}'".format(req.method, target_type_uri, expected)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': Request.blank(path='/v1/AUTH_0123456789/containername/testfile'),
                'expected': 'service/storage/object/account/container/object'
            },
            {
                'request': Request.blank(path='/v1/AUTH_0123456789/containername'),
                'expected': 'service/storage/object/account/container'
            },
            {
                'request': Request.blank(path='/v1/AUTH_0123456789'),
                'expected': 'service/storage/object/account'
            },
            {
                'request': Request.blank(path='/v1'),
                'expected': 'unknown'
            },
            {
                'request': Request.blank('/info'),
                'expected': 'service/storage/object/info'
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
