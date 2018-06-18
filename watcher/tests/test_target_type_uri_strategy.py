import unittest

from webob import Request

from . import fake
from watcher import target_type_uri_strategy as ttus

class TargetTypeURIStrategyTests(unittest.TestCase):
    isSetUp = False

    def setUp(self):
        if not self.isSetUp:
            self.generic = ttus.TargetTypeURIStrategy()
            self.nova = ttus.NovaTargetTypeURIStrategy()
            self.swift = ttus.SwiftTargetTypeURIStrategy()
            self.glance = ttus.GlanceTargetTypeURIStrategy()
            self.cinder = ttus.CinderTargetTypeURIStrategy()
            self.isSetUp = True

    def test_nova_action_target_type_uri(self):
        stimuli = [
            {
                'request': fake.create_request('/v2.1'),
                'expected': 'unknown'
            },
            {
                'request': fake.create_request('/v2.1/servers/0b1576c8-4928-46f5-8b99-e50de4f7f761'),
                'expected': 'service/compute/servers/server'
            },
            {
                'request': fake.create_request('/v2.1/flavors/0123456789abcdef0123456789abcdef/os-extra_specs'),
                'expected': 'service/compute/flavors/flavor/os-extra_specs'
            },
            {
                'request': fake.create_request('/v2.1/flavors/0123456789abcdef0123456789abcdef/os-extra_specs/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/flavors/flavor/os-extra_specs/key'
            },
            {
                'request': fake.create_request('/v2.1/os-floating-ip-dns/0123456789abcdef0123456789abcdef/entries/someentryname'),
                'expected': 'service/compute/os-floating-ip-dns/domain/entries/entry'
            },
            {
                'request': fake.create_request('/v2.1/os-floating-ips/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/os-floating-ips/floating-ip'
            },
            {
                'request': fake.create_request('/v2.1/os-hosts/somehostname/shutdown'),
                'expected': 'service/compute/os-hosts/host/shutdown'
            },
            {
                'request': fake.create_request('/v2.1/os-hypervisors/somehypervisorname/servers'),
                'expected': 'service/compute/os-hypervisors/hypervisor/servers'
            },
            {
                'request': fake.create_request('servers/0123456789abcdef0123456789abcdef/os-volume_attachments/0123456789abcdef0123456789abcdef'),
                'expected': 'service/compute/servers/server/os-volume_attachments/attachment'
            },
            {
                'request': fake.create_request(
                    path='/v2.1/servers/0123456789abcdef0123456789abcdef/action',
                    body_dict={'removeSecurityGroup': {'name': 'test'}}
                ),
                'expected': 'service/compute/servers/server/action'
            }
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            self.assertEqual(
                self.nova.determine_target_type_uri(req),
                expected,
                "target_type_uri of '{0}' should be '{1}'".format(req.path, expected)
            )

    def test_dns_get_recordsets_target_type_uri(self):
        req = fake.create_request(
            path='/v2/zones/0123456789abcdef0123456789abcdef/recordsets/0123456789abcdef0123456789abcdef')

        self.assertEqual(
            self.generic.determine_target_type_uri(req),
            'zones/zone/recordsets/recordset',
            "target_type_uri of '/v2/zones/<uid>/recordsets/<uid>' should be 'zones/zone/recordsets/recordset'"
        )

    def test_get_project_id_from_keystone_authentications_request(self):
        req = fake.create_request(path='auth/tokens', method='POST', body_dict={
            "auth": {
                "identity": {
                    "password": {
                        "user": {
                            "id": "71a7dcb0d60a43088a6c8e9b69a39e69",
                            "password": "devstack"
                        }
                    },
                    "methods": ["password"]
                },
                "scope": {
                    "project": {
                        "id": "194dfdddb6bc43e09701035b52edb0d9"
                    }
                },
                "type": "CREDENTIALS"
            }
        })

        self.assertEqual(
            self.generic.determine_target_type_uri(req),
            'auth/tokens',
        )

    def test_glance_target_type_uri(self):
        stimuli = [
            {
                'request': Request.blank(path='/v2/images'),
                'expected': 'service/storage/image/images'
            },
            {
                'request': Request.blank(path='/v2/images/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/image/images/image'
            },
            {
                'request': Request.blank(path='/v2/images/b206a1900310484f8a9504754c84b067/actions/deactivate'),
                'expected': 'service/storage/image/images/image/actions/deactivate'
            },
            {
                'request': Request.blank(path='/v2/images/b206a1900310484f8a9504754c84b067/members/123456789'),
                'expected': 'service/storage/image/images/image/members/member'
            },
            {
                'request': Request.blank(path='/v2/images/b206a1900310484f8a9504754c84b067/tags/foobar'),
                'expected': 'service/storage/image/images/image/tags/tag'
            },
            {
                'request': Request.blank(path='/v2/schemas/image'),
                'expected': 'service/storage/image/schemas/image'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            self.assertEqual(
                self.glance.determine_target_type_uri(req),
                expected,
                "target_type_uri of '{0}' should be '{1}'".format(req, expected)
            )


if __name__ == '__main__':
    unittest.main()
