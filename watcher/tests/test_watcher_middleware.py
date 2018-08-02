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

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


class TestWatcherMiddleware(unittest.TestCase):
    def setUp(self):
        self.watcher = OpenStackWatcherMiddleware(fake.FakeApp(), {})

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

        self.watcher.service_type = 'compute'
        self.assertEqual(
            self.watcher.get_target_project_id_from_keystone_token_info(token_info),
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

        self.watcher.service_type = 'compute'
        self.assertEqual(
            self.watcher.get_target_project_id_from_keystone_token_info(token_info),
            taxonomy.UNKNOWN,
            "should be 'unknown' as the service catalog contains no project scoped endpoint url"
        )


if __name__ == '__main__':
    unittest.main()
