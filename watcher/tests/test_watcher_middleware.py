# Copyright 2018 SAP SE
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six
import unittest

from pycadf import cadftaxonomy as taxonomy
from webob import Request

import watcher.common as common

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


class TestWatcherMiddleware(unittest.TestCase):
    def setUp(self):
        self.app = OpenStackWatcherMiddleware(fake.FakeApp(), {})

    def test_nova_get_servers_request(self):
        req = fake.create_request(path='servers/0123456789abcdef0123456789abcdef/action')
        self.app.service_type = 'compute'

        self.assertEqual(
            common.determine_cadf_action_from_request(req),
            taxonomy.ACTION_READ,
        )

    def test_nova_post_action(self):
        req = fake.create_request(
            path='v2.0/servers/0123456789abcdef0123456789abcdef/action',
            method='POST',
            body_dict={"addFloatingIp": {"address": "10.10.10.10", "fixed_address": "192.168.0.3"}},
        )
        self.app.service_type = 'compute'

        self.assertEqual(
            common.determine_cadf_action_from_request(req),
            taxonomy.ACTION_CREATE,
        )

    def test_designate_get_recordsets(self):
        req = fake.create_request(
            path='/v2/zones/0123456789abcdef0123456789abcdef/recordsets/0123456789abcdef0123456789abcdef')
        self.app.service_type = 'dns'

        self.assertEqual(
            common.determine_cadf_action_from_request(req),
            taxonomy.ACTION_READ,
        )

    def test_swift_put_object_request(self):
        req = fake.create_request(path='/v1/AUTH_account/container/object', method='PUT')
        self.app.service_type = 'object-storage'

        self.assertEqual(
            common.determine_cadf_action_from_request(req),
            taxonomy.ACTION_UPDATE,
        )

    def test_get_account_uid_and_container_name_from_request(self):
        stimuli = {
            '/v1/AUTH_0123456789/containername/testfile': ('0123456789', 'containername'),
        }

        for stim, expected in six.iteritems(stimuli):
            req = Request.blank(path=stim)
            req.method = 'PUT'

            self.assertEqual(
                self.app.get_target_account_container_id_from_request(req),
                expected
            )

    def test_get_target_project_id_from_keystone_token_info(self):
        token_info = {
            'token': {
                'catalog': [
                    {
                        'type': 'compute',
                        'id': '0123456789abcdef',
                        'name': 'nova',
                        'endpoints': [
                            {
                                'url': 'https://nova.local:8774/v2.1/194dfdddb6bc43e09701035b52edb0d9',
                                'interface': 'public',
                                'region': 'region',
                                'id': '0123456789abcdef'
                            }
                        ]
                    }
                ]
            }
        }

        self.app.service_type = 'compute'
        self.assertEqual(
            self.app.get_target_project_id_from_keystone_token_info(token_info),
            '194dfdddb6bc43e09701035b52edb0d9',
            "should be '194dfdddb6bc43e09701035b52edb0d9' as found in the service catalog"
        )

    def test_fail_get_target_project_id_from_keystone_token_info(self):
        token_info = {
            'token': {
                'catalog': [
                    {
                        'type': 'compute',
                        'id': '0123456789abcdef',
                        'name': 'nova',
                        'endpoints': [
                            {
                                'url': 'https://nova.local:8774/v2.1',
                                'interface': 'public',
                                'region': 'region',
                                'id': '0123456789abcdef'
                            }
                        ]
                    }
                ]
            }
        }

        self.app.service_type = 'compute'
        self.assertEqual(
            self.app.get_target_project_id_from_keystone_token_info(token_info),
            taxonomy.UNKNOWN,
            "should be 'unknown' as the service catalog contains no project scoped endpoint url"
        )


if __name__ == '__main__':
    unittest.main()
