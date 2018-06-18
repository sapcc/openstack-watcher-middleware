import os
import unittest

from webob import Request

from . import fake
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
DESIGNATE_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/designate.yaml'


class TestDesignate(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(fake.FakeApp(), {'service_type': 'dns'})
        self.is_setup = True

    def test_prefix(self):
        self.assertEqual(
            self.watcher.prefix,
            'service/dns',
            "service type is dns, hence the prefix should be 'service/dns'"
        )

    def test_cadf_action(self):
        raw_config = load_config(DESIGNATE_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the designate config should not be None")

        stimuli = [
            {
                'request': fake.create_request(
                    path='/v2/zones'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/b206a1900310484f8a9504754c84b067/nameservers'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/tasks/imports'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/tasks/transfer_requests',
                    method='PATCH'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(
                    path='/v2/reverse/floatingips'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2/reverse/floatingips/region:b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v2/reverse/floatingips/something'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v2/reverse/floatingips/something',
                    method='POST'
                ),
                'expected': 'create'
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
                'request': Request.blank(
                    path='/v2/zones'),
                'expected': 'service/dns/zones'
            },
            {
                'request': fake.create_request(
                    path='/v2/reverse/floatingips/region:b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/dns/reverse/floatingips/region/floatingip'
            },
            {
                'request': fake.create_request(
                    path='/v2/quotas/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/dns/quotas/quota'
            },
            {
                'request': fake.create_request(
                    path='/v2/blacklists/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/dns/blacklists/blacklist'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/b206a1900310484f8a9504754c84b067/recordsets/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/dns/zones/zone/recordsets/recordset'
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
