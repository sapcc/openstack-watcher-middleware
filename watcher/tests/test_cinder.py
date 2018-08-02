import os
import unittest

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
CINDER_CONFIG_PATH = WORKDIR + '/fixtures/cinder.yaml'


class TestCinder(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'volume',
                'config_file': CINDER_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_prefix(self):
        actual = self.watcher.strategy.target_type_uri_prefix
        expected = 'service/storage/block'
        self.assertEqual(
            actual,
            expected,
            "service type is volume, hence the prefix should be '{0}' but got '{1}'".format(expected, actual)
        )

    def test_cadf_action(self):
        stimuli = [
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/volumes/detail'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/detail'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshot/b206a1900310484f8a9504754c84b067/metadata/someKey'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/volumes'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-volume-transfer/b206a1900310484f8a9504754c84b067',
                    method='DELETE'
                ),
                'expected': 'delete'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/volumes',
                    method='POST'
                ),
                'expected': 'create'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    method='POST',
                    body_dict={'os-reset_status': {'status': 'available'}}
                ),
                'expected': 'update/os-reset_status'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    method='POST',
                    body_dict={'revert': {'snapshot_id': '5aa119a8-d25b-45a7-8d1b-88e127885635'}}
                ),
                'expected': 'update/revert'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/action',
                    method='POST',
                    body_dict={'os-force_delete': {}}
                ),
                'expected': 'update/os-force_delete'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/action',
                    method='POST',
                    body_dict={'delete': {'delete-volumes': 'False'}}
                ),
                'expected': 'update/delete'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-quota-sets/b206a1900310484f8a9504754c84b067?usage=True',
                ),
                'expected': 'read'
            },
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
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/types/type'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/extra_specs/somekey'),
                'expected': 'service/storage/block/types/type/extra_specs/extra_spec'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/encryption/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/types/type/encryption/encryption'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/os-volume-type-access'),
                'expected': 'service/storage/block/types/type/os-volume-type-access'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/volumes/b206a1900310484f8a9504754c84b067/metadata/somename'),
                'expected': 'service/storage/block/volumes/volume/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/metadata/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/snapshots/snapshot/metadata/key'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-volume-transfer/b206a1900310484f8a9504754c84b067/accept'),
                'expected': 'service/storage/block/os-volume-transfer/os-volume-transfer/accept'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-volume-transfer/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/os-volume-transfer/os-volume-transfer'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/attachments/b206a1900310484f8a9504754c84b067/action'),
                'expected': 'service/storage/block/attachments/attachment/action'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/capabilities/somehostname'),
                'expected': 'service/storage/block/capabilities/capability'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/consistencygroups/b206a1900310484f8a9504754c84b067/delete'),
                'expected': 'service/storage/block/consistencygroups/consistencygroup/delete'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/cgsnapshots/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/cgsnapshots/cgsnapshot'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_snapshots/b206a1900310484f8a9504754c84b067/action'),
                'expected': 'service/storage/block/group_snapshots/group_snapshot/action'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_types/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/group_types/group_type'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_types/b206a1900310484f8a9504754c84b067/group_specs/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/group_types/group_type/group_specs/group_spec'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-hosts/somehostname'),
                'expected': 'service/storage/block/os-hosts/os-host'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/qos-specs/b206a1900310484f8a9504754c84b067/disassociate_all'),
                'expected': 'service/storage/block/qos-specs/qos-spec/disassociate_all'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-quota-class-sets/quotaclassname'),
                'expected': 'service/storage/block/os-quota-class-sets/os-quota-class-set'
            },
            {
                'request': fake.create_request(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-quota-sets/b206a1900310484f8a9504754c84b067/defaults'),
                'expected': 'service/storage/block/os-quota-sets/os-quota-set/defaults'
            }
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
