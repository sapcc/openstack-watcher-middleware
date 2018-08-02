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
            'v3': True,
            'v2.0': True,
            'v2.542.2': True,
            'foobar': False,
            'vfoo.bar': False,
        }

        for stim, expected in six.iteritems(stimuli):
            self.assertEqual(
                common.is_version_string(stim),
                expected,
            )

    def test_is_uid_string(self):
        stimuli = {
            '7df1acb1a2f2478eadf3f350d3f44c51': True,
            '0123456789abcdef0123456789abcdef': True,
            'cb8b9823-1900-42b9-b7f4-b60adee456cb': True,
            '1a410d1f-2f62-4f79-bc94-c9b635144c51': True,
            'action': False,
            'auth': False,
            'v2': False
        }

        for stim, expected in six.iteritems(stimuli):
            is_uid = common.is_uid_string(stim)
            self.assertEqual(
                is_uid,
                expected
            )

    def test_trim_prefix(self):
        self.assertEqual(
            common.trim_prefix('service/storage/object/account/container', 'service/storage/object'),
            'account/container'
        )

        self.assertEqual(
            common.trim_prefix('service/compute/servers/action', 'service/foobar'),
            'service/compute/servers/action'
        )

    def test_get_project_id_from_path(self):
        stimuli = [
            {
                'path': '/v1/e9141fb24eee4b3e9f25ae69cda31132/foobar',
                'expected': 'e9141fb24eee4b3e9f25ae69cda31132',
                'help': "path '/v1/e9141fb24eee4b3e9f25ae69cda31132' contains the project id 'e9141fb24eee4b3e9f25ae69cda31132'"
            }
        ]

        for stim in stimuli:
            self.assertEqual(
                common.get_project_id_from_os_path(stim.get('path')),
                stim.get('expected'),
                stim.get('help')
            )


if __name__ == '__main__':
    unittest.main()
