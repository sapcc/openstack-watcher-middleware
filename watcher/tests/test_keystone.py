import os
import unittest

from pycadf import cadftaxonomy as taxonomy

from . import fake
from watcher.watcher import OpenStackWatcherMiddleware


WORKDIR = os.path.dirname(os.path.realpath(__file__))
KEYSTONE_CONFIG_PATH = WORKDIR + '/fixtures/keystone.yaml'


class TestKeystone(unittest.TestCase):
    is_setup = False

    def setUp(self):
        if self.is_setup:
            return
        self.watcher = OpenStackWatcherMiddleware(
            fake.FakeApp(),
            {
                'service_type': 'identity',
                'config_file': KEYSTONE_CONFIG_PATH
            }
        )
        self.is_setup = True

    def test_prefix(self):
        self.assertEqual(
            self.watcher.strategy.target_type_uri_prefix,
            'data/security',
            "service type is identity, hence the prefix should be 'data/security'"
        )

    def test_cadf_action(self):
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
                    path='/v3/ec2tokens',
                    method='POST',
                    body_dict={
                        "credentials": {
                            "access": "8cff51dc66594df4a2ae121f796df36c",
                            "host": "localhost",
                            "params": {
                                "Action": "Test",
                                "SignatureMethod": "HmacSHA256",
                                "SignatureVersion": "2",
                                "Timestamp": "2007-01-31T23:59:59Z"
                            },
                            "path": "/",
                            "secret": "df8daeaa981b40cea1217fead123bc64",
                            "signature": "Fra2UBKKtqy3GQ0mj+JqzR8GTGsbWQW+yN5Nih9ThfI=",
                            "verb": "GET"
                        }
                    }
                ),
                'expected': 'authenticate'
            },
            {
                'request': fake.create_request(
                    path='/v3/s3tokens',
                    method='POST',
                    body_dict={
                        "credentials": {
                            "access": "8cff51dc66594df4a2ae121f796df36c",
                            "host": "localhost",
                            "params": {
                                "Action": "Test",
                                "SignatureMethod": "HmacSHA256",
                                "SignatureVersion": "2",
                                "Timestamp": "2007-01-31T23:59:59Z"
                            },
                            "path": "/",
                            "secret": "df8daeaa981b40cea1217fead123bc64",
                            "signature": "Fra2UBKKtqy3GQ0mj+JqzR8GTGsbWQW+yN5Nih9ThfI=",
                            "verb": "GET"
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
            actual = self.watcher.determine_cadf_action(req)

            self.assertEqual(
                actual,
                expected,
                "cadf action for '{0} {1}' should be '{2}' but got '{3}'".format(req.method, req.path, expected, actual)
            )

    def test_target_type_uri(self):
        stimuli = [
            {
                'request': fake.create_request(path='/v3/regions/region-name'),
                'expected': 'data/security/regions/region'
            },
            {
                'request': fake.create_request(path='/v3/auth/tokens'),
                'expected': 'data/security/auth/tokens'
            },
            {
                'request': fake.create_request(path='/v3/ec2tokens'),
                'expected': 'data/security/ec2tokens'
            },
            {
                'request': fake.create_request(path='/v3/s3tokens'),
                'expected': 'data/security/s3tokens'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/config/b206a1900310484f8a9504754c84b067/ldap'
                ),
                'expected': 'data/security/domains/domain/config/group/option'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects'
                ),
                'expected': 'data/security/OS-INHERIT/domains/domain/groups/group/roles/inherited_to_projects'
            },
            {
                'request': fake.create_request(
                    path='/v3/OS-INHERIT/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles/inherited_to_projects',
                ),
                'expected': 'data/security/OS-INHERIT/domains/domain/users/user/roles/inherited_to_projects'
            },
            {
                'request': fake.create_request(path='/v3/auth/tokens/OS-PKI/revoked'),
                'expected': 'data/security/auth/tokens/OS-PKI/revoked'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'data/security/domains/domain/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'data/security/projects/project/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'
                ),
                'expected': 'data/security/projects/project/groups/group/roles'
            },
            {
                'request': fake.create_request(path='/v3/projects/p-4711asxc'),
                'expected': 'data/security/projects/project'
            },
            {
                'request': fake.create_request(
                    path='/v3/projects/b206a1900310484f8a9504754c84b067/tags/my-tag-name'
                ),
                'expected': 'data/security/projects/project/tags/tag'
            },
            {
                'request': fake.create_request(path='/v3/system/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'data/security/system/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/groups/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'data/security/domains/domain/groups/group/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067/roles'),
                'expected': 'data/security/domains/domain/users/user/roles'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/domain-name'),
                'expected': 'data/security/domains/domain'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/b206a1900310484f8a9504754c84b067'),
                'expected': 'data/security/users/user'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/d062392'),
                'expected': 'data/security/users/user'
            },
            {
                'request': fake.create_request(
                    path='/v3/users/b206a1900310484f8a9504754c84b067/groups'),
                'expected': 'data/security/users/user/groups'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/config/b206a1900310484f8a9504754c84b067/option/default'),
                'expected': 'data/security/domains/config/group/option/default'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/b206a1900310484f8a9504754c84b067/config/b206a1900310484f8a9504754c84b067'
                ),
                'expected': 'data/security/domains/domain/config/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/domains/config/b206a1900310484f8a9504754c84b067/default'
                ),
                'expected': 'data/security/domains/config/group/default'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067'),
                'expected': 'data/security/groups/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/my-group-name'),
                'expected': 'data/security/groups/group'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067/users'),
                'expected': 'data/security/groups/group/users'
            },
            {
                'request': fake.create_request(
                    path='/v3/groups/b206a1900310484f8a9504754c84b067/users/b206a1900310484f8a9504754c84b067'),
                'expected': 'data/security/groups/group/users/user'
            },
            {
                'request': fake.create_request(
                    path='/v3/limits/model'),
                'expected': 'data/security/limits/model'
            },
            {
                'request': fake.create_request(
                    path='/v3/limits/somelimit'),
                'expected': 'data/security/limits/limit'
            },
            {
                'request': fake.create_request(
                    path='/v3/limits/b206a1900310484f8a9504754c84b067'),
                'expected': 'data/security/limits/limit'
            },
            {
                'request': fake.create_request(
                    path='/v3'),
                'expected': 'data/security/versions'
            },
            {
                'request': fake.create_request(
                    path='/'),
                'expected': 'data/security/root'
            }
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
                self.watcher.get_project_domain_and_user_id_from_keystone_authentication_request(req),
                s.get('expected'),
            )


if __name__ == '__main__':
    unittest.main()
