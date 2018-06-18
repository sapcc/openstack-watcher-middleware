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

import json
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


def determine_cadf_action_from_request(req):
    """
    determines the cadf action from a request

    :param req: the request
    :return: the cadf action or None
    """
    return determine_cadf_action(req.method, req.path)


def determine_cadf_action(method, path=''):
    """
    determines action based on request method and path

    :param method: the request method
    :param path: the request path
    :return: the action or unknown
    """
    # remove trailing '/'
    path = path.rstrip('/')
    # POST ../auth/tokens is an authentication request
    if method == 'POST' and 'auth/tokens' in path:
        return taxonomy.ACTION_AUTHENTICATE
    # GET ../detail requests are always read/list
    if method == 'GET' and path.endswith('/detail'):
        return taxonomy.ACTION_LIST
    # try to map everything else based on http method
    for m_string, tax_action in six.iteritems(method_action_map):
        if m_string.lower() == method.lower():
            return tax_action
    return taxonomy.UNKNOWN


def determine_custom_cadf_action(config, target_type_uri, method='GET', os_action=None, prefix=None):
    """
    Per default the action is determined by the determine_action(req) method based on the requests method
    and, in case of an authentication request, a portion of the request path.
    More granular actions can be defined via configuration and are mapped in this method.

    :param config: the custom action configuration
    :param target_type_uri: the request path without uids, e.g.: 'compute/servers/action'
    :param method: the request's method
    :param os_action: the openstack action if applicable
    :param prefix: the target_type_uri's prefix
    :return: the custom action as per config or unknown
    """
    custom_action = taxonomy.UNKNOWN
    target_type_uri = split_prefix_target_type_uri(target_type_uri, prefix)
    uri_parts = target_type_uri.split('/')
    part_config = config

    if not uri_parts:
        return custom_action

    # include openstack action if it's an../action request but avoid duplication
    # pep8 says 'os_action in uri_parts' is bad practice, so we do:
    if os_action and not [itm for itm in uri_parts if itm == os_action]:
        uri_parts.append(os_action)

    try:
        for part in uri_parts:
            is_last_part = part == uri_parts[-1]
            if isinstance(part_config, dict):
                conf = part_config.get(part, None)
                if conf:
                    part_config = conf
            elif isinstance(part_config, list):
                conf = _find_key_in_list(part, part_config)
                if not conf:
                    break
                part_config = conf
            # if this is the last part of the target_type_uri, look for the action_type, which
            # might be directly accessible (string) or part of a list, which looks like:
            # [ {method: <http_method>, action_type: <action_type}, {..} ]
            if is_last_part:
                if isinstance(part_config, str):
                    custom_action = part_config
                    break
                elif isinstance(part_config, list):
                    custom_action = _find_custom_cadf_action_in_list(method, part_config)
                    break
    finally:
        return custom_action


def _find_key_in_list(key, list_to_search):
    for itm in list_to_search:
        part_config = itm.get(key, None)
        if part_config:
            return part_config
    return None


def _find_custom_cadf_action_in_list(method, config_list):
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


def determine_openstack_action_from_request(req):
    """
    get openstack action from request's json body
    consider only request with 'action' in path and payload is json

    request:
        path: '/v2.1/servers/0123456789abcdef0123456789abcdef/action'
        body: {'addFloatingIp': ... }
    result:
        action: addFloatingIp

    :param req: the request with json payload
    :return: the action or None
    """
    action = None
    # return here if not 'action' in path and body not json
    if not is_action_request(req):
        return action

    try:
        json_body = req.json
        if json_body:
            d = json.loads(json_body)
            # the 1st key specifies the action type
            action = next(iter(d))
            if action:
                return action
    except Exception:
        pass
    finally:
        return action


def openstack_action_to_cadf_action(os_action, os_prefix='os-', cadf_prefix='update/'):
    """
    in most cases the openstack action can be converted to a cadf action simply by:
    (1) removing os_prefix from the os_action
    (2) adding a cadf_prefix to the cadf action

    :param os_action: the openstack action as found in a request body
    :param os_prefix: prefix to trim from the os_action
    :param cadf_prefix: prefix to the cadf action
    :return: the cadf action
    """
    if not os_action:
        return taxonomy.UNKNOWN
    return cadf_prefix + os_action.lstrip(os_prefix)


def string_to_bool(bool_string):
    return bool_string.lower() == 'true'
