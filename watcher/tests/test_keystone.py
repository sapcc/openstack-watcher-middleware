import os
import unittest

from webob import Request
from pycadf import cadftaxonomy as taxonomy

from . import fake
import watcher.common as common
from watcher.watcher import load_config
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
KEYSTONE_COMPLEX_CONFIG_PATH = WORKDIR + '/fixtures/keystone.yaml'


class TestKeystone(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(fake.FakeApp(), {'service_type': 'identity'})
        self.is_setup = True

    def test_prefix(self):
        self.assertEqual(
            self.watcher.prefix,
            'service/identity',
            "service type is identity, hence the prefix should be 'service/identity'"
        )

    def test_cadf_action(self):
        raw_config = load_config(KEYSTONE_COMPLEX_CONFIG_PATH)
        config = raw_config.get('custom_actions', None)
        self.assertIsNotNone(config, "the keystone config should not be None")

        stimuli = [
            {
                'request': fake.create_request(
                    path='/v3/auth/tokens',
                    method='POST',
                    body_dict={
                        "auth": {
                            "identity": {
                                "methods": [
                                    "password"
                                ],
                                "password": {
                                    "user": {
                                        "id": "ee4dfb6e5540447cb3741905149d9b6e",
                                        "password": "devstacker"
                                    }
                                }
                            },
                            "scope": {
                                "project": {
                                    "id": "a6944d763bf64ee6a275f1263fae0352"
                                }
                            }
                        }
                    }
                ),
                'expected': 'authenticate'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/config/b206a1900310484f8a9504754c84b067/ldap'
                ),
                'expected': 'read'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects',
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v3/auth/tokens/OS-PKI/revoked'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(path='/v3/system/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'read/list'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'read/list'
            }
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            target_type_uri = self.watcher.determine_target_type_uri(req)
            actual_cadf_action = self.watcher.determine_cadf_action(config, target_type_uri, req)

            self.assertIsNotNone(target_type_uri, 'target.type_uri for req {0} must not be None'.format(req))
            self.assertIsNot(target_type_uri, 'unknown',
                             "target.type_uri for req {0} must not be 'unknown'".format(req))

            self.assertEqual(
                actual_cadf_action,
                expected,
                "cadf action for '{0} {1}' should be '{2}' but got '{3}'".format(req.method, target_type_uri, expected, actual_cadf_action)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': Request.blank(path='/v3/regions/region-name'),
                'expected': 'service/identity/regions/region'
            },
            {
                'request': Request.blank(path='/v3/auth/tokens'),
                'expected': 'service/identity/auth/tokens'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/config/b206a1900310484f8a9504754c84b067/ldap'
                ),
                'expected': 'service/identity/domains/domain/config/group/option'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects'
                ),
                'expected': 'service/identity/OS-INHERIT/domains/domain/groups/group/roles/inherited_to_projects'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects',
                ),
                'expected': 'service/identity/OS-INHERIT/domains/domain/users/user/roles/inherited_to_projects'
            },
            {
                'request': fake.create_request(path='/v3/auth/tokens/OS-PKI/revoked'),
                'expected': 'service/identity/auth/tokens/OS-PKI/revoked'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'service/identity/domains/domain/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'service/identity/projects/project/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'service/identity/projects/project/groups/group/roles'
            },
            {
                'request': Request.blank(path='/v3/projects/p-4711asxc'),
                'expected': 'service/identity/projects/project'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/tags/my-tag-name'
                ),
                'expected': 'service/identity/projects/project/tags/tag'
            },
            {
                'request': fake.create_request(path='/v3/system/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'service/identity/system/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'service/identity/domains/domain/groups/group/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'service/identity/domains/domain/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/domain-name'),
                'expected': 'service/identity/domains/domain'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/identity/users/user'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/d062392'),
                'expected': 'service/identity/users/user'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/b206a1900310484f8a9504754c84b067/groups'),
                'expected': 'service/identity/users/user/groups'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/config/b206a1900310484f8a9504754c84b067/option/default'),
                'expected': 'service/identity/domains/config/group/option/default'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/config/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'service/identity/domains/domain/config/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/config/b206a1900310484f8a9504754c84b067/default'
                ),
                'expected': 'service/identity/domains/config/group/default'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/identity/groups/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/my-group-name'),
                'expected': 'service/identity/groups/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067/users'),
                'expected': 'service/identity/groups/group/users'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067'),
                'expected': 'service/identity/groups/group/users/user'
            },
        ]

        for stim in stimuli:
            req = stim.get('request')
            expected = stim.get('expected')
            actual = self.watcher.determine_target_type_uri(req)
            self.assertEqual(
                actual,
                expected,
                "target_type_uri of '{0} {1}' should be '{2}' but got '{3}'"
                .format(req.method, req.path, expected, actual)
            )

    def test_get_target_project_domain_and_user_id_from_keystone_authentication_request(self):
        stimuli = [
            {
                'body':
                    {
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
                    },
                'expected': ('194dfdddb6bc43e09701035b52edb0d9', taxonomy.UNKNOWN, '71a7dcb0d60a43088a6c8e9b69a39e69')
            },
            {
                'body':
                    {
                        "auth": {
                            "identity": {
                                "methods": [
                                    "password"
                                ],
                                "password": {
                                    "user": {
                                        "name": "admin",
                                        "domain": {
                                            "name": "Default"
                                        },
                                        "password": "devstacker"
                                    }
                                }
                            }
                        }
                    },
                'expected': (taxonomy.UNKNOWN, taxonomy.UNKNOWN, taxonomy.UNKNOWN)
            },
            {
                'body':
                    {
                        "auth": {
                            "identity": {
                                "methods": [
                                    "token"
                                ],
                                "token": {
                                    "id": "'$OS_TOKEN'"
                                }
                            },
                            "scope": {
                                "domain": {
                                    "id": "default"
                                }
                            }
                        }
                    },
                'expected': (taxonomy.UNKNOWN, 'default', taxonomy.UNKNOWN)
            },
            {
                'body':
                    {
                        "auth": {
                            "identity": {
                                "methods": [
                                    "token"
                                ],
                                "token": {
                                    "id": "'$OS_TOKEN'"
                                }
                            },
                            "scope": {
                                "project": {
                                    "id": "a6944d763bf64ee6a275f1263fae0352"
                                }
                            }
                        }
                    },
                'expected': ('a6944d763bf64ee6a275f1263fae0352', taxonomy.UNKNOWN, taxonomy.UNKNOWN)
            },
            {
                'body':
                    {
                        "auth": {
                            "identity": {
                                "methods": [
                                    "token"
                                ],
                                "token": {
                                    "id": "'$OS_TOKEN'"
                                }
                            },
                            "scope": "unscoped"
                        }
                    },
                'expected': (taxonomy.UNKNOWN, taxonomy.UNKNOWN, taxonomy.UNKNOWN)
            }
        ]

        for s in stimuli:
            req = fake.create_request(path='auth/tokens', method='POST', body_dict=s.get('body'))

            self.assertEqual(
                common.determine_cadf_action_from_request(req),
                taxonomy.ACTION_AUTHENTICATE,
            )

            self.assertEqual(
                self.watcher.get_project_domain_and_user_id_from_keystone_authentication_request(req),
                s.get('expected'),
            )


if __name__ == '__main__':
    unittest.main()
