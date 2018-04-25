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


import json

from pycadf import cadftaxonomy as taxonomy

from . import common


class TargetTypeURIStrategy(object):
    """
    base class for target type uri strategies
    """
    def __init__(self, strategy, prefix=None):
        self.strategy = strategy
        self.prefix = prefix

    def determine_target_type_uri(self, request):
        """
        determine target type uri from a request path and body
        evaluating the request body might be necessary for e.g. compute actions

        :param request: the request
        :return: the target type uri or 'unknown'
        """
        raise NotImplementedError

    def add_prefix_target_type_uri(self, target_type_uri):
        """
        adds the prefix to the target type uri

        :param target_type_uri: the target type uri as per cadf specification
        :return: prefixed target type uri
        """
        return common.add_prefix_target_type_uri(target_type_uri, self.prefix)

    def split_prefix_target_type_uri(self, target_type_uri):
        """
        removes the prefix from the target type uri

        :param target_type_uri: the target type uri as per cadf specification
        :return: the target_type_uri without prefix
        """
        return common.split_prefix_target_type_uri(target_type_uri, self.prefix)


class GenericTargetTypeURIStrategy(TargetTypeURIStrategy):
    """
    constructs the resource key from the request path or body

    examples:
    (1) path: .../v2/zones/012345678abcdef/recordsets/012345678abcdef
        => <prefix>/zones/zone/recordsets

    (2) path: .../servers/1234567890abcdef/action
        body: {"addFloatingIp": {"address": "x.x.x.x", "fixed_address": "x.x.x.x"}
        => <prefix>/servers/server/addFloatingIp
    """
    def __init__(self, prefix=None):
        super(GenericTargetTypeURIStrategy, self).__init__(strategy='generic', prefix=prefix)

    def determine_target_type_uri(self, req):
        """
        :param req: the request
        :return: the resource key
        """
        target_type_uri = []
        try:
            path_parts = req.path.lstrip('/').split('/')

            # no /action request. concat path without version or uids
            for index, part in enumerate(path_parts):
                is_uid = common.is_uid_string(part)
                previous_index = index - 1
                if is_uid and previous_index >= 0:
                    # replace uid with resource using previous part in singular
                    # ../servers/<uid>/.. => ../servers/server/..
                    target_type_uri.append(path_parts[previous_index].rstrip('s'))
                    continue
                if common.is_version_string(part):
                    continue
                if len(part) > 1:
                    target_type_uri.append(part)

            # action request: determine action from body
            if common.is_action_request(req):
                json_body = req.json
                if json_body:
                    d = json.loads(json_body)
                    # the 1st key specifies the action type
                    itm = next(iter(d))
                    if itm:
                        target_type_uri.append(itm)

        except (AttributeError, ValueError) as e:
            self.logger.warning("failed to parse request body: %s" % str(e))
            target_type_uri = []
        except Exception as e:
            self.logger.warning("failed to get target_type_uri from request path: %s" % str(e))
            target_type_uri = []
        finally:
            # we just have the service
            if len(target_type_uri) < 1:
                return taxonomy.UNKNOWN
            uri = '/'.join(target_type_uri).lstrip('/')
            return self.add_prefix_target_type_uri(uri)


class SwiftTargetTypeURIStrategy(TargetTypeURIStrategy):
    """
    determines the target_type_uri from a swift request

    path of swift request might look like:  ../AUTH_accountname/containername/objectname
    and the corresponding target_type_uri like: <prefix>/account/container/object
    """
    def __init__(self, strategy='swift', prefix='service/storage/object'):
        super(SwiftTargetTypeURIStrategy, self).__init__(strategy=strategy, prefix=prefix)

    def determine_target_type_uri(self, req):
        """
        :param req: the swift request
        :return: the target_type_uri or taxonomy.UNKNOWN
        """
        target_type_uri = []
        try:
            account_id, container_id, object_id = common.get_swift_account_container_object_id_from_path(req.path)
            if account_id and account_id != taxonomy.UNKNOWN:
                target_type_uri.append('account')
            if container_id and container_id != taxonomy.UNKNOWN:
                target_type_uri.append('container')
            if object_id and object_id != taxonomy.UNKNOWN:
                target_type_uri.append('object')
        finally:
            if len(target_type_uri) < 1:
                return taxonomy.UNKNOWN
            uri = '/'.join(target_type_uri).lstrip('/')
            return self.add_prefix_target_type_uri(uri)
