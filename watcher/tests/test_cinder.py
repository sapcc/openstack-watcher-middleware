import os
import unittest

from webob import Request

from . import fake
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
CINDER_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/cinder.yaml'


class TestCinder(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(fake.FakeApp(), {})
        self.watcher.service_type = 'volume'
        self.watcher.cadf_service_name = 'service/storage/block'
        self.is_setup = True

    def test_cadf_action(self):
        raw_config = load_config(CINDER_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the cinder config should not be None")

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
                'expected': 'update/reset_status'
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
                'expected': 'update/force_delete'
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
            target_type_uri = self.watcher.determine_target_type_uri(req)
            self.assertIsNotNone(target_type_uri, 'target.type_uri for req {0} must not be None'.format(req))
            self.assertIsNot(target_type_uri, 'unknown', "target.type_uri for req {0} must not be 'unknown'".format(req))

            self.assertEqual(
                self.watcher.determine_cadf_action(config, target_type_uri, req),
                expected,
                "cadf action for '{0} {1}' should be '{2}'".format(req.method, target_type_uri, expected)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/types/type'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/extra_specs/somekey'),
                'expected': 'service/storage/block/types/type/extra_specs/key'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/encryption/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/types/type/encryption/key'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/types/b206a1900310484f8a9504754c84b067/os-volume-type-access'),
                'expected': 'service/storage/block/types/type/os-volume-type-access'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/volumes/b206a1900310484f8a9504754c84b067/metadata/somename'),
                'expected': 'service/storage/block/volumes/volume/metadata/key'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/snapshots/b206a1900310484f8a9504754c84b067/metadata/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/snapshots/snapshot/metadata/key'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-volume-transfer/b206a1900310484f8a9504754c84b067/accept'),
                'expected': 'service/storage/block/os-volume-transfer/transfer/accept'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-volume-transfer/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/os-volume-transfer/transfer'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/attachments/b206a1900310484f8a9504754c84b067/action'),
                'expected': 'service/storage/block/attachments/attachment/action'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/capabilities/somehostname'),
                'expected': 'service/storage/block/capabilities/host'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/consistencygroups/b206a1900310484f8a9504754c84b067/delete'),
                'expected': 'service/storage/block/consistencygroups/consistencygroup/delete'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/cgsnapshots/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/cgsnapshots/cgsnapshot'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_snapshots/b206a1900310484f8a9504754c84b067/action'),
                'expected': 'service/storage/block/group_snapshots/snapshot/action'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_types/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/group_types/type'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/group_types/b206a1900310484f8a9504754c84b067/group_specs/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/storage/block/group_types/type/group_specs/spec'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-hosts/somehostname'),
                'expected': 'service/storage/block/os-hosts/host'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/qos-specs/b206a1900310484f8a9504754c84b067/disassociate_all'),
                'expected': 'service/storage/block/qos-specs/spec/disassociate_all'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-quota-class-sets/quotaclassname'),
                'expected': 'service/storage/block/os-quota-class-sets/class'
            },
            {
                'request': Request.blank(
                    path='/v3/b206a1900310484f8a9504754c84b067/os-quota-sets/b206a1900310484f8a9504754c84b067/defaults'),
                'expected': 'service/storage/block/os-quota-sets/quota/defaults'
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
