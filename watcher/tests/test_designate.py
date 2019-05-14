import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
DESIGNATE_CONFIG_PATH = WORKDIR + '/fixtures/designate.yaml'


class TestDesignate(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'dns',
                'config_file': DESIGNATE_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_prefix(self):
        self.assertEqual(
            self.watcher.strategy.target_type_uri_prefix,
            'service/dns',
            "service type is dns, hence the prefix should be 'service/dns'"
        )

    def test_cadf_action(self):
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
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/myzone/recordsets/myrecordset'
                ),
                'expected': 'service/dns/zones/zone/recordsets/recordset'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/tasks/imports/myzone'
                ),
                'expected': 'service/dns/zones/tasks/imports/import'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/zone_id/tasks/export'
                ),
                'expected': 'service/dns/zones/zone/tasks/export'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/tasks/exports/export'
                ),
                'expected': 'service/dns/zones/tasks/exports/export'
            },
            {
                'request': fake.create_request(
                    path='/v2/zones/tasks/exports/foobar/export'
                ),
                'expected': 'service/dns/zones/tasks/exports/export/export'
            },
            {
                'request': fake.create_request(
                    path='/v2'
                ),
                'expected': 'service/dns/versions'
            },
            {
                'request': fake.create_request(
                    path='/'
                ),
                'expected': 'service/dns/root'
            },
            {
                'request': fake.create_request(
                    path=''
                ),
                'expected': 'service/dns/root'
            },
            {
              'request': fake.create_request(
                  path='/v2/zones/something.com'
              ),
              'expected': 'service/dns/zones/zone'
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
