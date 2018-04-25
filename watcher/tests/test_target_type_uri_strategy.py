import six
import unittest
import json

from webob import Request

from watcher import target_type_uri_strategy as ttus


def create_request(path, method='GET', body_dict=None):
    r = Request.blank(path=path)
    r.method = method
    if body_dict:
        r.json_body = json.dumps(body_dict)
        r.content_type = 'application/json'
    return r


class TargetTypeURIStrategyTests(unittest.TestCase):
    isSetUp = False

    def setUp(self):
        if not self.isSetUp:
            self.generic = ttus.GenericTargetTypeURIStrategy()
            self.swift = ttus.SwiftTargetTypeURIStrategy()
            self.isSetUp = True

    def test_nova_post_action_target_type_uri(self):
        req = create_request(
            path='/v2.0/servers/0123456789abcdef0123456789abcdef/action',
            method='POST',
            body_dict={"addFloatingIp": {"address": "10.10.10.10", "fixed_address": "192.168.0.3"}},
        )

        self.assertEqual(
            self.generic.determine_target_type_uri(req),
            'servers/server/action/addFloatingIp',
            "target_type_uri of path='/v2.0/servers/0123456789abcdef0123456789abcdef/action', body='{addFloatingIp: ..}' should be 'servers/server/action/addFloatingIp'"
        )

    def test_designate_get_recordsets_target_type_uri(self):
        req = create_request(
            path='/v2/zones/0123456789abcdef0123456789abcdef/recordsets/0123456789abcdef0123456789abcdef')

        self.assertEqual(
            self.generic.determine_target_type_uri(req),
            'zones/zone/recordsets/recordset',
            "target_type_uri of '/v2/zones/0123456789abcdef0123456789abcdef/recordsets/0123456789abcdef0123456789abcdef' should be 'zones/zone/recordsets/recordset'"
        )

    def test_get_project_id_from_keystone_authentications_request(self):
        req = create_request(path='auth/tokens', method='POST', body_dict={
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

    def test_swift_target_type_uri(self):
        stimuli = [
            {
                'request': Request.blank(path='/v1/AUTH_0123456789/containername/testfile'),
                'expected': 'service/storage/object/account/container/object',
                'help': "target_type_uri of '/v1/AUTH_0123456789/containername/testfile' should be 'service/storage/object/account/container/object'"
            },
            {
                'request': Request.blank(path='/v1/AUTH_0123456789/containername'),
                'expected': 'service/storage/object/account/container',
                'help': "target_type_uri of '/v1/AUTH_0123456789/containername' should be 'service/storage/object/account/container'"
            },
            {
                'request': Request.blank(path='/v1/AUTH_0123456789'),
                'expected': 'service/storage/object/account',
                'help': "target_type_uri of '/v1/AUTH_0123456789' should be 'service/storage/object/account'"
            },
            {
                'request': Request.blank(path='/v1'),
                'expected': 'unknown',
                'help': "target_type_uri of '/v1' should be 'unknown"
            }
        ]

        for stim in stimuli:
            self.assertEqual(
                self.swift.determine_target_type_uri(stim.get('request')),
                stim.get('expected'),
                stim.get('help')
            )


if __name__ == '__main__':
    unittest.main()
