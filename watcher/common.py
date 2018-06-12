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


method_action_map = {
    'GET': taxonomy.ACTION_READ,
    'HEAD': taxonomy.ACTION_READ,
    'PUT': taxonomy.ACTION_UPDATE,
    'PATCH': taxonomy.ACTION_UPDATE,
    'POST': taxonomy.ACTION_CREATE,
    'DELETE': taxonomy.ACTION_DELETE,
    'COPY': 'create/copy'
}


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


def determine_action_from_request(req):
    """
    determines the cadf action from a request

    :param req: the request
    :return: the cadf action or None
    """
    return determine_action(req.method, req.path)


def determine_action(method, path=''):
    if method == 'POST' and 'auth/tokens' in path:
        # must be an authentication request
        return taxonomy.ACTION_AUTHENTICATE
    # try to map everything else
    for m_string, tax_action in six.iteritems(method_action_map):
        if m_string.lower() == method.lower():
            return tax_action
    return taxonomy.UNKNOWN


def determine_custom_action(config, target_type_uri, method='GET', prefix=None):
    """
    Per default the action is determined by the determine_action(req) method based on the requests method
    and, in case of an authentication request, a portion of the request path.
    More granular actions can be defined via configuration and are mapped in this method.

    :param config: the custom action configuration
    :param target_type_uri: the request path without uids, e.g.: 'compute/servers/action/addFloatingIp'
    :param method: optional HTTP method
    :param prefix: the target_type_uri's prefix
    :return: the custom action as per config or unknown
    """
    custom_action = taxonomy.UNKNOWN
    target_type_uri = split_prefix_target_type_uri(target_type_uri, prefix)
    uri_parts = target_type_uri.split('/')
    part_config = config

    if not uri_parts:
        return custom_action

    for index, part in enumerate(uri_parts):
        if isinstance(part_config, dict):
            conf = part_config.get(part, None)
            if conf:
                part_config = conf
        # if this is the last part of the target_type_uri, look for the custom_action config, which
        # might be directly accessible (string) or if multiple custom actions are defined,
        # be part of a list [ {method: <http_method>, action: <custom_action>}, {..} ]
        if index == len(uri_parts) - 1:
            if isinstance(part_config, str):
                return part_config
            elif isinstance(part_config, list):
                return _find_custom_action_in_list(method, part_config)
        # not the last part of target_type_uri, but found a list:
        # look deeper until end reached or a configuration was found
        if isinstance(part_config, list):
            for itm in part_config:
                conf = itm.get(uri_parts[index + 1], None)
                if conf:
                    return determine_custom_action(conf, target_type_uri, method)
    return custom_action


def add_prefix_target_type_uri(target_type_uri, prefix):
    if not prefix:
        return target_type_uri
    prefix = prefix.lstrip('/')
    if not prefix.endswith('/') and not target_type_uri.startswith('/'):
        prefix += '/'
    return prefix + target_type_uri


def split_prefix_target_type_uri(target_type_uri, prefix):
    if prefix and target_type_uri.startswith(prefix):
        target_type_uri = target_type_uri[len(prefix):]
    return target_type_uri.lstrip('/')


def _find_custom_action_in_list(method, config_list):
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


def is_action_request(req):
    """
    check whether the request is an action
    containing a json body

    :param req: the request
    :return: bool whether the request is an action
    """
    return 'action' in req.path and _is_content_json(req)


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


def get_swift_project_id_from_path(path):
    """
    get the project id (aka account id) from swift request path

    :param path: the swift request path or unknown
    :return: the project id or unknown
    """
    project_id, _, _ = get_swift_account_container_object_id_from_path(path)
    return project_id


def get_swift_account_container_object_id_from_path(path):
    path_regex = re.compile(
        r'/\S+AUTH_(?P<account_id>[p\-]?[0-9a-fA-F-]+?)(\/+?|$)'
        r'(?P<container_id>\S*?)(\/+?|$)'
        r'(?P<object_id>\S*?)(\/+?|$)'
    )
    account_id = container_id = object_id = taxonomy.UNKNOWN
    try:
        match = path_regex.match(path)
        account_id = match.group('account_id') or account_id
        container_id = match.group('container_id') or container_id
        object_id = match.group('object_id') or object_id
    finally:
        return account_id, container_id, object_id


def _is_content_json(req):
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
    uid_pattern = re.compile('[a-fA-F0-9-?]{32,36}')
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
    version_pattern = re.compile('^v(?:\d+\.)?(?:\d+\.)?(\*|\d+)$')
    if version_pattern.match(string):
        return True
    return False


def string_to_bool(bool_string):
    return bool_string.lower() == 'true'
