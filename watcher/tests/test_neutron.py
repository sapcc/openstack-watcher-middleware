import os
import unittest

from webob import Request

from . import fake
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
NEUTRON_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/neutron.yaml'


class TestDesignate(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {'service_type': 'network'}
        )
        self.is_setup = True

    def test_prefix(self):
        self.assertEqual(
            self.watcher.prefix,
            'service/network',
            "service type is network, hence the prefix should be 'service/network'"
        )

    def test_cadf_action(self):
        raw_config = load_config(NEUTRON_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the neutron config should not be None")

        stimuli = [
            {
                'request': fake.create_request(path='/v2.0/networks'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/networks/b206a1900310484f8a9504754c84b067',
                    method='PUT'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/trunks/b206a1900310484f8a9504754c84b067/get_subports'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/fw/firewall_policies/b206a1900310484f8a9504754c84b067/remove_rule',
                    method='PUT'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/flavors/b206a1900310484f8a9504754c84b067/service_profiles/b206a1900310484f8a9504754c84b067',
                    method='DELETE'
                ),
                'expected': 'delete'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/quotas/b206a1900310484f8a9504754c84b067',
                    method='PUT'
                ),
                'expected': 'update'
            },
            {
                'request': fake.create_request(path='/v2.0/quotas'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v2.0/quotas/b206a1900310484f8a9504754c84b067'),
                'expected': 'read'
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
                'request': fake.create_request(path='/v2.0/networks'),
                'expected': 'service/network/networks'
            },
            {
                'request': fake.create_request(path='/v2.0/trunks/b206a1900310484f8a9504754c84b067/add_subports'),
                'expected': 'service/network/trunks/trunk/add_subports'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/fwaas/firewall_policies/b206a1900310484f8a9504754c84b067/remove_rule'
                ),
                'expected': 'service/network/fwaas/firewall_policies/firewall_policy/remove_rule'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/network-ip-availabilities/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/network/network-ip-availabilities/availability'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/qos/policies/b206a1900310484f8a9504754c84b067/dscp_marking_rules/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/network/qos/policies/policy/dscp_marking_rules/rule'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/someresourcetype/b206a1900310484f8a9504754c84b067/tags'
                ),
                'expected': 'service/network/resource_type/resource/tags'
            },
            {
                'request': fake.create_request(
                    path='/v2.0/someresourcetype/b206a1900310484f8a9504754c84b067/tags/tagname'
                ),
                'expected': 'service/network/resource_type/resource/tags/tag'
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
