# Copyright 2018 SAP SE
#
# Licensed under the Apache License, Version 2.0 (the 'License'); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six
import unittest

from pycadf import cadftaxonomy as taxonomy

import watcher.common as common


class TestCommon(unittest.TestCase):
    def test_is_version_string(self):
        stimuli = {
            'v2': True,
            'v2.0': True,
            'v2.542.2': True,
            'foobar': False,
            'vfoo.bar': False,
        }

        for stim, expected in six.iteritems(stimuli):
            self.assertEqual(
                common.is_version_string(stim),
                expected
            )

    def test_is_uid_string(self):
        stimuli = {
            '7df1acb1a2f2478eadf3f350d3f44c51': True,
            '0123456789abcdef0123456789abcdef': True,
            'cb8b9823-1900-42b9-b7f4-b60adee456cb': True,
            '1a410d1f-2f62-4f79-bc94-c9b635144c51': True,
            'action': False,
            'auth': False,
            'v2': False,
        }

        for stim, expected in six.iteritems(stimuli):
            is_uid = common.is_uid_string(stim)
            self.assertEqual(
                is_uid,
                expected
            )

    def test_split_prefix_target_type_uri(self):
        self.assertEqual(
            common.split_prefix_target_type_uri('service/storage/object/account/container', 'service/storage/object'),
            'account/container'
        )

        self.assertEqual(
            common.split_prefix_target_type_uri('service/compute/servers/action/addFloatingIp', 'service/compute'),
            'servers/action/addFloatingIp'
        )

        self.assertEqual(
            common.split_prefix_target_type_uri('service/compute/servers/action/addFloatingIp', 'service/foobar'),
            'service/compute/servers/action/addFloatingIp'
        )

    def test_custom_action_nova(self):
        config = {
           'servers': [
                {'detail': 'read/list'},
                {'action':[
                    {'addFloatingIp': 'update/addFloatingIp'},
                    {'removeFloatingIp': 'update/removeFloatingIp'},
                ]}
            ],
           'flavors': [
                {'detail': 'read/list'},
                {'action': [
                    {'addTenantAccess': 'add/project-access'},
                    {'removeTenantAccess': 'remove/project-access'}
                ]}
            ]
        }

        stimuli = [
            {
                'target_type_uri': 'compute/servers/action/addFloatingIp',
                'expected': 'update/addFloatingIp',
                'help': "the custom action of 'POST compute/servers/action/addFloatingIp' should be 'update/addFloatingIp'"
            },
            {
                'target_type_uri': 'compute/servers/detail',
                'expected': 'read/list',
                'help': "the custom action of 'GET compute/servers/detail' should be 'read/list'"
            },
            {
                'target_type_uri': 'compute/flavors/action/addTenantAccess',
                'expected': 'add/project-access',
                'help': "the custom action of 'POST compute/flavors/action/addTenantAccess' should be 'add/project-access'"
            },
            {
                'target_type_uri': 'compute/flavors/action/removeTenantAccess',
                'expected': 'remove/project-access',
                'help': "the custom action of 'POST compute/flavors/action/removeTenantAccess' should be 'remove/project-access'"
            }
        ]

        for s in stimuli:
            self.assertEqual(
                common.determine_custom_action(config, s.get('target_type_uri')),
                s.get('expected'),
                s.get('help')
            )

    def test_custom_action_swift(self):
        config = {
            'account': [
                {
                    'method': 'GET',
                    'action': 'read/list'
                },
                {
                    'method': 'POST',
                    'action': 'update'
                },
                {
                    'container': [
                        {
                            'method': 'GET',
                            'action': 'read/list'
                        },
                        {
                            'method': 'POST',
                            'action': 'update'
                        },
                        {
                          'method': 'HEAD',
                          'action': 'read',
                        },
                        {
                            'object': [
                                {
                                    'method': 'POST',
                                    'action': 'update'
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        stimuli = [
            {
                'method': 'GET',
                'target_type_uri': 'service/storage/object/account',
                'expected': 'read/list',
                'help': "the custom action of 'GET /account' should be 'read/list'"
            },
            {
                'method': 'HEAD',
                'target_type_uri': 'service/storage/object/account',
                'expected': 'unknown',
                'help': "the custom action of 'HEAD /account' should be 'unknown'"
            },
            {
                'method': 'POST',
                'target_type_uri': 'service/storage/object/account',
                'expected': 'update',
                'help': "the custom action of 'POST /account' should be 'update'"
            },
            {
                'method': 'GET',
                'target_type_uri': 'service/storage/object/account/container',
                'expected': 'read/list',
                'help': "the custom action of 'GET /account/container' should be 'read/list'"
            },
            {
                'method': 'HEAD',
                'target_type_uri': 'service/storage/object/account/container',
                'expected': 'read',
                'help': "the custom action of 'HEAD /account/container' should be 'read'"
            },
            {
                'method': 'POST',
                'target_type_uri': 'service/storage/object/account/container',
                'expected': 'update',
                'help': "the custom action of 'POST /account/container' should be 'update'"
            },
            {
                'method': 'POST',
                'target_type_uri': 'service/object/account/container/object',
                'expected': 'update',
                'help': "the custom action of 'POST /account/container/object' should be 'update'"
            }
        ]

        for s in stimuli:
            target_type_uri = s.get('target_type_uri')
            method = s.get('method')
            custom_action = common.determine_custom_action(config, target_type_uri, method, prefix='service/storage/object')

            self.assertEqual(
                custom_action,
                s.get('expected'),
                s.get('help')
            )

    def test_get_project_id_from_path(self):
        stimuli = [
            {
                'path': '/v1/e9141fb24eee4b3e9f25ae69cda31132/foobar',
                'expected': 'e9141fb24eee4b3e9f25ae69cda31132',
                'help': "path '/v1/e9141fb24eee4b3e9f25ae69cda31132' contains the project id 'e9141fb24eee4b3e9f25ae69cda31132'"
            },
        ]

        for stim in stimuli:
            self.assertEqual(
                common.get_project_id_from_os_path(stim.get('path')),
                stim.get('expected'),
                stim.get('help')
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
                'expected': taxonomy.UNKNOWN,
                'help': "'v1/foo/bar' does not contain a swift project id"
            }
        ]

        for stim in stimuli:
            self.assertEqual(
                common.get_swift_project_id_from_path(stim.get('path')),
                stim.get('expected'),
                stim.get('help')
            )


if __name__ == '__main__':
    unittest.main()
