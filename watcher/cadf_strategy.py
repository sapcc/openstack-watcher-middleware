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

import logging
import re
import six

from pycadf import cadftaxonomy as taxonomy

from . import common


class BaseCADFStrategy(object):
    """
    constructs the target_type_uri from the request path and body

    examples:
    (1) path: .../v2/zones/012345678abcdef/recordsets/012345678abcdef
        => <prefix>/zones/zone/recordsets/recordset

    (2) path: .../servers/1234567890abcdef/action
        body: {"addFloatingIp": {"address": "x.x.x.x", "fixed_address": "x.x.x.x"}
        => <prefix>/servers/server/addFloatingIp
    """
    def __init__(
            self, name='base',
            target_type_uri_prefix=None,
            regex_mapping=[],
            path_keywords=[],
            keyword_exclusions=[],
            custom_action_config={},
            logger=logging.getLogger(__name__)):
        """
        base strategy to determine the CADF target type URI and CADF action of a request

        :param name: name of the strategy
        :param target_type_uri_prefix: prefix to add to the target_type_uri
        :param regex_mapping: list of mapping of {<request_path>: <target_type_uri>}
        :param path_keywords: list of service specific keywords
        :param keyword_exclusions: list of keyword exclusions, which will never be replaced
        :param logger: the logger to use
        """
        self.name = name
        self.target_type_uri_prefix = target_type_uri_prefix
        self.logger = logger
        self.regex_mapping = regex_mapping
        self.custom_action_config = custom_action_config
        # prefix to apply to the openstack action found in a json body
        self.cadf_os_action_prefix = 'update/'

        # defaults keywords in request path
        # example:
        # ../metadata/someMetadataKey => ../metadata/key
        default_path_keywords = [
            'tags',
            {'metadata': 'key'}
        ]
        # do not replace the following. even if they appear after a keyword
        # example:
        # path: shares/<share_id>   => target_type_uri: shares/share
        # path: shares/detail       => target_type_uri: shares/detail
        default_keyword_exclusions = \
            [
                'detail', 'default', 'info', 'capacities', 'root', 'create', 'delete', 'update', 'action', 'enable',
                'disable', 'force', 'force-down', 'add', 'remove', 'reboot', 'shutdown', 'startup', 'root', 'consoles',
                'health', 'healthz'
            ]

        if path_keywords:
            self.path_keywords = default_path_keywords + path_keywords
        else:
            self.path_keywords = default_path_keywords

        if keyword_exclusions:
            self.keyword_exclusions = default_keyword_exclusions + keyword_exclusions
        else:
            self.keyword_exclusions = default_keyword_exclusions

    def get_cadf_service_name(self):
        """
        get the service name according to the CADF spec

        :return: the cadf service name or unknown
        """
        if common.is_none_or_unknown(self.target_type_uri_prefix):
            return taxonomy.UNKNOWN
        return self.target_type_uri_prefix

    def determine_target_type_uri(self, req):
        """
        determines the target.type_uri of a request by its path in the following order:
        (1 a) check whether any of the given regular expressions matches the path
        (1 b) check whether any of the given keywords appear in the path
        (2)   determine target type URI part by part (especially helpful if neither regex' nor keywords are given)

        :param req: the request
        :return: the target.type_uri or 'unknown'
        """
        # remove '/' at beginning and end
        target_type_uri = taxonomy.UNKNOWN
        try:
            path = req.path.lstrip('/').rstrip('/')

            # check for root path
            if path == '' or path == '/':
                target_type_uri = 'root'
                return

            # check whether path ends with a version
            if common.endswith_version(path):
                target_type_uri = 'versions'
                return

            # path handled by regex?
            target_type_uri = self._determine_target_type_uri_by_regex(path)
            if common.is_none_or_unknown(target_type_uri):
                # split path by remaining '/' and evaluate part by part to ensure versions,
                # uids, etc. are properly replaced
                # default if neither regex nor keywords are configured
                target_type_uri = self._determine_target_type_uri_by_parts(path.split('/'))

        except Exception as e:
            self.logger.debug(
                "exception while determining the target type URI of '{0} {1}': {2}".format(req.method, req.path, str(e))
            )

        finally:
            if common.is_none_or_unknown(target_type_uri):
                self.logger.debug("failed to determine target type URI of '{0} {1}'".format(req.method, req.path))
                return

            return self._add_prefix_target_type_uri(target_type_uri)

    def determine_cadf_action(self, req, target_type_uri=None):
        """
        determine the CADF action of a request

        :param req: the request
        :param target_type_uri: (optional) the target type URI of the request path if already known.
                                will attempt to determine otherwise
        :return: the CADF action of unknown
        """
        cadf_action = taxonomy.UNKNOWN

        # is this an ../action request with a json body, then check the json body for the openstack action
        if common.is_action_request(req):
            cadf_action = self._cadf_action_from_body(req.json)

        # get target type URI from request path if still unknown
        if common.is_none_or_unknown(target_type_uri):
            target_type_uri = self.determine_target_type_uri(req)

        # lookup action in custom mapping if one exists
        if self.custom_action_config:
            custom_cadf_action = self._cadf_action_from_custom_action_config(target_type_uri, req.method, cadf_action)
            if not common.is_none_or_unknown(custom_cadf_action):
                cadf_action = custom_cadf_action

        # if nothing was found, return cadf action based on request method and path
        if common.is_none_or_unknown(cadf_action):
            cadf_action = self._cadf_action_from_method_and_target_type_uri(req.method, target_type_uri)

        return cadf_action

    def _cadf_action_from_method_and_target_type_uri(self, method, path):
        """
        determines action based on request method and path

        :param method: the request method
        :param path: the request path
        :return: the action or unknown
        """
        path = path.rstrip('/')
        # POST ../auth/tokens is an authentication request
        if method == 'POST' and 'auth/tokens' in path:
            return taxonomy.ACTION_AUTHENTICATE

        if method == 'POST' and 's3tokens' in path:
            return taxonomy.ACTION_AUTHENTICATE

        if method == 'POST' and 'ec2tokens' in path:
            return taxonomy.ACTION_AUTHENTICATE

        if method == 'GET':
            if path.endswith('/detail'):
                return taxonomy.ACTION_LIST
            # if path ends with any keyword: it's a read/list
            for k in self.path_keywords:
                keyword = k
                if isinstance(k, dict):
                    keyword = list(k.keys())[0]
                if path.endswith('/' + keyword):
                    return taxonomy.ACTION_LIST

        # try to map everything else based on http method
        for m_string, tax_action in six.iteritems(common.METHOD_ACTION_MAP):
            if m_string.lower() == method.lower():
                return tax_action

        return taxonomy.UNKNOWN

    def _cadf_action_from_body(self, json_body):
        """
        get OpenStack action from requests json body

        request:
            path: '/v2.1/servers/0123456789abcdef0123456789abcdef/action'
            body: {'os-addFloatingIp': ... }
        result:
            cadf action: update/addFloatingIp

        :param json_body: request's json body
        :param os_prefix: prefix of the action in the json body (default: 'os-')
        :param cadf_prefix: prefix to apply according to cadf spec (default: 'update/')
        :return: the cadf action of unknown
        """
        cadf_action = taxonomy.UNKNOWN
        try:
            if isinstance(json_body, str) or isinstance(json_body, six.string_types):
                json_body = common.load_json_dict(json_body)
            # the 1st key specifies the action type
            os_action = next(iter(json_body))
            # avoid empty string '""'
            if os_action and len(os_action) > 2:
                # add prefix to os_action
                cadf_action = self.cadf_os_action_prefix + str(os_action)
                return
        except Exception as e:
            self.logger.debug("error while determining action from json body: {0}".format(str(e)))

        finally:
            return cadf_action

    def _cadf_action_from_custom_action_config(self, target_type_uri, method='GET', os_action=None):
        """
        looks up a a custom mapping of target type URI to CADF action

        :param target_type_uri: the request's target type URI
        :param method: the request method
        :param os_action: optional. the openstack action as found in the json body of the request
        :return: the CADF action according to the custom mapping
        """
        custom_action = taxonomy.UNKNOWN

        # return here, if no custom mapping is configured or the target type URI is not known
        if not self.custom_action_config or common.is_none_or_unknown(target_type_uri):
            return custom_action

        target_type_uri_without_prefix = \
            self._split_prefix_target_type_uri(target_type_uri)
        target_type_uri_parts = target_type_uri_without_prefix.split('/')

        # include os_action as found in json body of request but avoid duplication
        if not common.is_none_or_unknown(os_action) and not [itm for itm in target_type_uri_parts if itm == os_action]:
            # trim the prefix from an openstack action and append to target_type_uri for lookup of custom action
            # example:
            # os_action:         update/addFloatingIP
            # target_type_uri:   servers/server/action/addFloatingIp
            target_type_uri_parts.append(
                common.trim_prefix(os_action, self.cadf_os_action_prefix)
            )
        part_config = self.custom_action_config

        try:
            for part in target_type_uri_parts:
                is_last_part = part == target_type_uri_parts[-1]
                if isinstance(part_config, dict):
                    conf = part_config.get(part, None)
                    if conf:
                        part_config = conf
                elif isinstance(part_config, list):
                    conf = common.find_key_in_list(part, part_config)
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
                        custom_action = common.find_custom_cadf_action_in_list(method, part_config)
                        break
        finally:
            return custom_action

    def _determine_target_type_uri_by_regex(self, path):
        """
        some path' can only be handled via regex
        example: neutron tag extension
        path:              '/v2.0/{resource_type}/{resource_id}/tags'
        target_type_uri:   'service/network/resource_type/resource/tags'

        :param req: the request
        :return: the target_type_uri
        """
        for mapping in self.regex_mapping:
            try:
                regex = list(mapping.keys())[0]
                replacement = list(mapping.values())[0]
                new_path = re.sub(
                    regex,
                    replacement,
                    path
                )
                # return if something was replaced
                if path != new_path:
                    return new_path

            except Exception as e:
                self.logger.debug('failed to apply regex {0} to path: {1}: {2}'.format(regex, path, e))
                continue

        # return 'None' if path is unchanged or new path
        return None

    def _determine_target_type_uri_by_parts(self, path_parts):
        """
        main method to determine the target type URI of an request

        :param path_parts: list of path split by '/'
        :return: the target type URI or unknown
        """
        target_type_uri = []
        try:
            for index, part in enumerate(path_parts):
                # append part or, if it's a uid, append the replacement
                # using replace_uid_with_singular_or_custom_action_config()
                # servers/<uid>/ => servers/server, policies/<uid> => policies/policy
                previous_index = index - 1
                if previous_index >= 0:
                    p = self._check_parts(path_parts[previous_index], part)
                    if p:
                        target_type_uri.append(p)
                        continue
                # ensure no versions or uids are added to the target_type_uri even if the path starts with one
                if common.is_version_string(part) or common.is_uid_string(part):
                    continue
                elif common.is_timestamp_string(part):
                    target_type_uri.append('version')
                    continue
                if len(part) > 1:
                    target_type_uri.append(part)

        except Exception as e:
            self.logger.debug("failed to get target_type_uri from request path: %s" % str(e))
            target_type_uri = []
        finally:
            # we need at least one part
            if len(target_type_uri) < 1:
                return None
            # finally build the string from the parts
            return '/'.join(target_type_uri).lstrip('/')

    def _add_prefix_target_type_uri(self, target_type_uri):
        """
        adds the prefix to the target type uri

        :param target_type_uri: the target type uri as per cadf specification
        :return: prefixed target type uri
        """
        return common.add_prefix(target_type_uri, self.target_type_uri_prefix)

    def _split_prefix_target_type_uri(self, target_type_uri):
        """
        removes the prefix from the target type uri

        :param target_type_uri: the target type uri as per cadf specification
        :return: the target_type_uri without prefix
        """
        return common.trim_prefix(target_type_uri, self.target_type_uri_prefix)

    def _get_singular_from_keyword(self, keyword):
        """
        returns the singular of a given keyword which is either derived or provided by a
        custom mapping


        :param keyword: the path keyword
        :return: the keyword in singular
        """
        # check whether a custom mapping of { <keyword_plural>: <keyword_singular> } exists
        for k in self.path_keywords:
            if isinstance(k, dict):
                keyword_singular = list(k.values())[0]
                if list(k.keys())[0] == keyword and keyword_singular:
                    return keyword_singular

        # replace plural ending with 'ies' by singular ending with 'y'
        if keyword.endswith('ies'):
            return keyword.rstrip('ies') + 'y'
        return keyword.rstrip('s')

    def _check_parts(self, previous_part, part):
        """
        returns the singular of the previous part by removing the trailing 's' to replace the uid
        if the singular cannot be derived this way, a mapping is required

        example:
        (1) ../servers/<uid>/.. => ../servers/server/..
        (2) mapping{'os-extra_specs': 'key'}
            ../os-extra_specs/<uid>/.. => ../os-extra_specs/key/..

        :param previous_part: the previous part of the path
        :param part: the current path part
        :return: part for the target_type_uri
        """
        # ignore if previous part is version as in /v3/<project_id>/.. or /v3/<path_keyword>/
        if common.is_version_string(previous_part):
            return None
        # replace plural ending with 'ies' by singular ending with 'y'
        if common.is_uid_string(part):
            return self._get_singular_from_keyword(previous_part)
        if self._is_keyword_in_keywords(previous_part) and \
                not self._is_keyword_in_keywords(part) and \
                part not in self.keyword_exclusions:
            return self._get_singular_from_keyword(previous_part)
        return None

    def _is_keyword_in_keywords(self, keyword):
        """
        checks whether a given keyword can be found in the list of keywords.
        handled by a method, since the list of keywords can contain strings or dictionaries

        :param keyword: the keyword to look for
        :return: bool whether it was found
        """
        for k in self.path_keywords:
            kwd = k
            if isinstance(k, dict):
                kwd = list(k.keys())[0]
            if keyword == kwd:
                return True
        return False


class SwiftCADFStrategy(BaseCADFStrategy):
    """
    determines the target_type_uri from a swift (object-store) request

    path of swift request might look like:  ../AUTH_accountname/containername/objectname
    and the corresponding target_type_uri like: <prefix>/account/container/object
    """
    def __init__(self,
                 target_type_uri_prefix=None, regex_mapping=[],
                 path_keywords=[], keyword_exclusions=[],
                 custom_action_config={}, logger=logging.getLogger(__name__)):
        # init
        super(SwiftCADFStrategy, self).__init__(
            self,
            target_type_uri_prefix=target_type_uri_prefix, regex_mapping=regex_mapping,
            path_keywords=path_keywords, keyword_exclusions=keyword_exclusions,
            custom_action_config=custom_action_config, logger=logger
        )
        self.name = 'object-store'

    def determine_target_type_uri(self, req):
        """
        determine the target type URI of a swift request

        :param req: the swift request
        :return: the target_type_uri or unknown
        """
        target_type_uri = []

        # handle a path with these endings before applying any regex
        path_endings = {
            '/v1': 'versions',
            '/info': 'info',
            '/endpoints': 'endpoints'
        }

        try:
            path = req.path

            # check for empty path
            if path == '' or path == '/':
                target_type_uri.append('root')
                return

            # check for static endings
            for ending in list(path_endings.keys()):
                if path.endswith(ending):
                    target_type_uri.append(path_endings.get(ending))
                    return

            account_id, container_id, object_id = self.get_swift_account_container_object_id_from_path(path)
            if not common.is_none_or_unknown(account_id):
                target_type_uri.append('account')
            if not common.is_none_or_unknown(container_id):
                target_type_uri.append('container')
            if not common.is_none_or_unknown(object_id):
                target_type_uri.append('object')

        except Exception as e:
            self.logger.debug("error while determining target type URI from request '{0} {1}': {2}"
                              .format(req.method, req.path, str(e)))

        finally:
            if len(target_type_uri) < 1:
                self.logger.debug("failed to determine target type URI of '{0} {1}'".format(req.method, req.path))
                return taxonomy.UNKNOWN
            # merge, add prefix and return
            uri = '/'.join(target_type_uri).lstrip('/')
            return self._add_prefix_target_type_uri(uri)

    def get_swift_account_container_object_id_from_path(self, path):
        path_regex = re.compile(
            r'/\S+AUTH_(?P<account_id>\S*?)(\/+?|$)'
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

    def get_swift_project_id_from_path(self, path):
        """
        get the project id (aka account id) from swift request path

        :param path: the swift request path or unknown
        :return: the project id or unknown
        """
        project_id, _, _ = self.get_swift_account_container_object_id_from_path(path)
        return project_id
