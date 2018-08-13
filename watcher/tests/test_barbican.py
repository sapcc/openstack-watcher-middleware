import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
BARBICAN_CONFIG_PATH = WORKDIR + '/fixtures/barbican.yaml'


class TestIronic(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            config={
                'service_type': 'key-manager',
                'config_file': BARBICAN_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_prefix(self):
        expected = 'service/security/keymanager'
        actual = self.watcher.strategy.target_type_uri_prefix

        self.assertEqual(
            actual,
            expected,
            "service type is barbican, hence the prefix should be '{0}' but got '{1}'".format(expected, actual)
        )

    def test_cadf_action(self):
        stimuli = [
            {
                'request': fake.create_request(path='/v1/orders'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/orders/0123456789abcdef0123456789abcdef'),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path='/v1/secrets'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/secrets/0123456789abcdef0123456789abcdef'),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path='/v1/secret-stores'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/containers/0123456789abcdef0123456789abcdef/secrets'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v1/containers/0123456789abcdef0123456789abcdef/acl'),
                'expected': 'read'
            },
            {
                'request': fake.create_request(path='mycontainer/consumers'),
                'expected': 'read/list'
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
                    path='/v1'),
                'expected': 'service/security/keymanager/versions'
            },
            {
                'request': fake.create_request(
                    path='/v1/orders'),
                'expected': 'service/security/keymanager/orders'
            },
            {
                'request': fake.create_request(
                    path='/v1/orders/0123456789abcdef0123456789abcdef'),
                'expected': 'service/security/keymanager/orders/order'
            },
            {
                'request': fake.create_request(
                    path='/v1/orders/myorder'),
                'expected': 'service/security/keymanager/orders/order'
            },
            {
                'request': fake.create_request(
                    path='/v1/secrets/0123456789abcdef0123456789abcdef/payload'),
                'expected': 'service/security/keymanager/secrets/secret/payload'
            },
            {
                'request': fake.create_request(
                    path='/v1/secrets/0123456789abcdef0123456789abcdef'),
                'expected': 'service/security/keymanager/secrets/secret'
            },
            {
                'request': fake.create_request(
                    path='/v1/secrets/0123456789abcdef0123456789abcdef/metadata'),
                'expected': 'service/security/keymanager/secrets/secret/metadata'
            },
            {
                'request': fake.create_request(
                    path='/v1/secrets/0123456789abcdef0123456789abcdef/metadata/foobar'),
                'expected': 'service/security/keymanager/secrets/secret/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/v1/secret-stores'),
                'expected': 'service/security/keymanager/secret-stores'
            },
            {
                'request': fake.create_request(
                    path='/v1/secret-stores/{secret_store_id}'),
                'expected': 'service/security/keymanager/secret-stores/secret-store'
            },
            {
              'request': fake.create_request(
                  path='/v1/secret-stores/preferred'),
              'expected': 'service/security/keymanager/secret-stores/preferred'
            },
            {
                'request': fake.create_request(
                    path='/v1/secret-stores/global-default'),
                'expected': 'service/security/keymanager/secret-stores/global-default'
            },
            {
                'request': fake.create_request(
                    path='/v1/containers'),
                'expected': 'service/security/keymanager/containers'
            },
            {
                'request': fake.create_request(
                    path='/v1/containers/0123456789abcdef0123456789abcdef'),
                'expected': 'service/security/keymanager/containers/container'
            },
            {
                'request': fake.create_request(
                    path='/v1/containers/0123456789abcdef0123456789abcdef/secrets'),
                'expected': 'service/security/keymanager/containers/container/secrets'
            },
            {
                'request': fake.create_request(
                    path='/v1/secrets/0123456789abcdef0123456789abcdef/acl'),
                'expected': 'service/security/keymanager/secrets/secret/acl'
            },
            {
                'request': fake.create_request(
                    path='/v1/containers/0123456789abcdef0123456789abcdef/acl'),
                'expected': 'service/security/keymanager/containers/container/acl'
            },
            {
                'request': fake.create_request(
                    path='/v1/quotas'),
                'expected': 'service/security/keymanager/quotas'
            },
            {
                'request': fake.create_request(
                    path='/v1/project-quotas/0123456789abcdef0123456789abcdef'),
                'expected': 'service/security/keymanager/project-quotas/project-quota'
            },
            {
                'request': fake.create_request(
                    path='0123456789abcdef0123456789abcdef/consumers'),
                'expected': 'service/security/keymanager/container/consumers'
            },
            {
                'request': fake.create_request(
                    path='mycontainer/consumers'),
                'expected': 'service/security/keymanager/container/consumers'
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
