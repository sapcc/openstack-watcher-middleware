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

import unittest
import os

from watcher.watcher import load_config


WORKDIR = os.path.dirname(os.path.realpath(__file__))
NOVA_CONFIG_PATH = WORKDIR + '/fixtures/nova.yaml'
SWIFT_CONFIG_PATH = WORKDIR + '/fixtures/swift.yaml'


class MyTestCase(unittest.TestCase):
    def test_load_config_nova(self):
        expected = {
            'os-snapshots': [
                {
                    'method': 'GET',
                    'action': 'read/list'
                },
                {
                    'detail': 'read/list'
                }
            ],
            'os-volumes': [
                {
                    'method': 'GET',
                    'action': 'read/list'
                },
                {
                    'detail': 'read/list'
                }
            ],
            'os-volume-types': [
                {
                    'method': 'GET',
                    'action': 'read/list'
                }
            ],
            'servers': [
                {
                    'detail': 'read/list'
                },
                {
                    'action':
                        [
                            { 'addFloatingIp': 'update/addFloatingIp' },
                            { 'removeFloatingIp': 'update/removeFloatingIp'},
                        ]

                }
            ],
            'flavors': [
                {
                    'detail': 'read/list'
                },
                {
                    'action':
                        [
                            {'addTenantAccess': 'add/project-access'},
                            {'removeTenantAccess': 'remove/project-access'}
                        ]
                }
            ]
        }

        cfg = load_config(NOVA_CONFIG_PATH)
        self.assertIsNotNone(cfg)
        self.assertEqual(
            cfg.get('custom_actions'),
            expected
        )

    def test_load_config_swift(self):
        expected = {
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

        cfg = load_config(SWIFT_CONFIG_PATH)
        self.assertIsNotNone(cfg)
        self.assertEqual(
            cfg.get('custom_actions', None),
            expected
        )


if __name__ == '__main__':
    unittest.main()
