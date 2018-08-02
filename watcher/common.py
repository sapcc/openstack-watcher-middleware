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

import re
import six

from pycadf import cadftaxonomy as taxonomy


UID_REGEX = '[a-fA-F0-9-?]{32,36}'
VERSION_REGEX = '^v(?:\d+\.)?(?:\d+\.)?(\*|\d+)$'

METHOD_ACTION_MAP = {
    'GET': taxonomy.ACTION_READ,
    'HEAD': taxonomy.ACTION_READ,
    'PUT': taxonomy.ACTION_UPDATE,
    'PATCH': taxonomy.ACTION_UPDATE,
    'POST': taxonomy.ACTION_CREATE,
    'DELETE': taxonomy.ACTION_DELETE,
    'COPY': 'create/copy'
}

# Mapping of service type to CADF prefix
# Only required if CADF prefix != service/<service_type>
SERVICE_TYPE_CADF_PREFIX_MAP = {
    'object-store': 'service/storage/object',
    'image': 'service/storage/image',
    'volume': 'service/storage/block',
    'identity': 'data/security',
    'share': 'service/storage/share',
    'baremetal': 'service/compute/baremetal'
}


def is_none_or_unknown(thing):
    """
    check if a thing is None or unknown

    :param thing: the cadf action, cadf target_type_uri, ..
    :return: bool whether thing is None or unknown
    """
    return thing is None or thing == taxonomy.UNKNOWN


def find_domain_id_in_auth_dict(auth_dict):
    return _find_id_in_dict(auth_dict, 'domain')


def find_project_id_in_auth_dict(auth_dict):
    return _find_id_in_dict(auth_dict, 'project')


def find_user_id_in_auth_dict(auth_dict):
    return _find_id_in_dict(auth_dict, 'user')


def _find_id_in_dict(d, key):
    for k, v in six.iteritems(d):
        if k == key:
            return v.get('id', taxonomy.UNKNOWN)
        elif isinstance(v, dict):
            id = _find_id_in_dict(v, key)
            if id != taxonomy.UNKNOWN:
                return id
    return taxonomy.UNKNOWN


def find_key_in_list(key, list_to_search):
    for itm in list_to_search:
        part_config = itm.get(key, None)
        if part_config:
            return part_config
    return None


def find_custom_cadf_action_in_list(method, config_list):
    """
    returns the custom action in a list of configurations for a target or UNKNOWN
    l = [{'method': 'GET', 'action': 'read/list'}, .. ]

    :param method: the HTTP method
    :param l: the list of configurations
    :return: the custom action or UNKNOWN
    """
    for config in config_list:
        method_string = config.get('method', '')
        action = config.get('action_type', None)
        if method_string.lower() == method.lower() and action:
            return action
    return taxonomy.UNKNOWN


def add_prefix(string_to_add, prefix):
    prefix = prefix.lstrip('/')
    # avoid double slashes
    if not prefix.endswith('/') and not string_to_add.startswith('/'):
        prefix += '/'
    return prefix + string_to_add


def trim_prefix(string_to_trim, prefix):
    if prefix and string_to_trim.startswith(prefix):
        string_to_trim = string_to_trim[len(prefix):]
    return string_to_trim.lstrip('/')


def is_action_request(req):
    """
    check whether the request is an action
    containing a json body

    :param req: the request
    :return: bool whether the request is an action
    """
    return 'action' in req.path and is_content_json(req)


def is_swift_request(path):
    """
    check whether the request path contains /AUTH_account as seen in swift requests

    :param path: the request path
    :return: bool whether it's a swift request or not
    """
    if '/AUTH_' in path:
        return True
    return False


def get_project_id_from_os_path(path):
    """
    get the project uid from a path if there's one
    path must be something like ../<version>/<project_id>/..
    version must follow regex: '^v(?:\d+\.)?(?:\d+\.)?(\*|\d+)$'
    (v1,v1.0,..)

    :param path: path containing a project uid
    :return: the project uid or unknown
    """
    path_regex = re.compile(r'\S+v(?:\d+\.)?(?:\d+\.)?(\*|\d+)/(?P<project_id>[a-fA-F0-9-?]{32,36})(/|$)')
    match = path_regex.match(path)
    if match and match.group('project_id'):
        return match.group('project_id')
    return taxonomy.UNKNOWN


def is_content_json(req):
    """
    check whether the content of a request is json

    :param req: the request
    :return: bool
    """
    return req.content_type == 'application/json' \
        and int(req.content_length) > 0


def is_uid_string(string):
    """
    check if the string is a uid

    :param string: the string in question
    :return: bool, whether the string is a uid or not
    """
    uid_pattern = re.compile(UID_REGEX)
    match = uid_pattern.match(string)
    if match:
        return True
    return False


def is_version_string(string):
    """
    check if the string is a version string
    :param string: version string 'v2' or 'v2.0'
    :return: bool
    """
    version_pattern = re.compile(VERSION_REGEX)
    if version_pattern.match(string):
        return True
    return False


def endswith_version(string):
    """
    check whether a string ends with a version

    :param string: the string to check
    :return: bool whether the string ends with a version
    """
    version_ending_pattern = re.compile('\S*v(?:\d+\.)?(?:\d+\.)?(\*|\d+)$')
    if version_ending_pattern.match(string.rstrip('/')):
        return True
    return False


def string_to_bool(bool_string):
    return bool_string.lower() == 'true'
