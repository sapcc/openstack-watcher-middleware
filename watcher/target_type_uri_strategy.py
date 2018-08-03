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

from pycadf import cadftaxonomy as taxonomy

from . import common


class TargetTypeURIStrategy(object):
    """
    constructs the target_type_uri from the request path and body

    examples:
    (1) path: .../v2/zones/012345678abcdef/recordsets/012345678abcdef
        => <prefix>/zones/zone/recordsets/recordset

    (2) path: .../servers/1234567890abcdef/action
        body: {"addFloatingIp": {"address": "x.x.x.x", "fixed_address": "x.x.x.x"}
        => <prefix>/servers/server/addFloatingIp
    """
    def __init__(self, name='generic', prefix=None, mapping={}, regex_mapping={}, logger=logging.getLogger(__name__)):
        """
        a strategy to determine the target.type_uri

        :param strategy: the name of the strategy
        :param prefix: the prefix to apply to the target.type_uri
               in most cases: service/<service_type>
        :param mapping: the mapping of {plural: singular}
               only required if the singular != plural.rstrip(s)
               example: {'service_profiles': 'profile'}
        :param regex_mapping: mapping of { regex : replacement }
               used to replace parts of the path
        :param logger: the logger
        """
        self.name = name
        self.prefix = prefix
        self.logger = logger
        self.mapping = mapping
        self.regex_mapping = regex_mapping

    def determine_target_type_uri(self, req):
        """
        determines the target.type_uri of a request by its path

        :param req: the request
        :return: the target.type_uri or 'unknown'
        """
        # remove '/' at beginning and end. split by remaining '/'
        path = req.path.lstrip('/').rstrip('/')
        path_after_regex = self._apply_regex_to_path(path)
        return self._determine_target_type_uri_by_parts(path_after_regex.split('/')) or taxonomy.UNKNOWN

    def _determine_target_type_uri_by_parts(self, path_parts):
        target_type_uri = []
        try:
            for index, part in enumerate(path_parts):
                # append part or, if it's a uid, append the replacement
                # using replace_uid_with_singular_or_custom_mapping()
                # servers/<uid>/ => servers/server, policies/<uid> => policies/policy
                previous_index = index - 1
                if previous_index >= 0:
                    p = self._replace_uid_with_singular_or_custom_mapping(path_parts[previous_index], part)
                    if p:
                        target_type_uri.append(p)
                        continue
                # ensure no versions or uids are added to the target_type_uri even if the path starts with one
                if common.is_version_string(part) or common.is_uid_string(part):
                    continue
                if len(part) > 1:
                    target_type_uri.append(part)

        except Exception as e:
            self.logger.warning("failed to get target_type_uri from request path: %s" % str(e))
            target_type_uri = []
        finally:
            # we need at least one part
            if len(target_type_uri) < 1:
                return None
            # finally build the string from the parts and add the prefix service/<service_type>
            uri = '/'.join(target_type_uri).lstrip('/')
            return self.add_prefix_target_type_uri(uri)

    def _apply_regex_to_path(self, path):
        """
        some path' can only be handled via regex.
        for instance: neutron tag extension: '/v2.0/{resource_type}/{resource_id}/tags'

        :param req: the request
        :return: the target_type_uri
        """
        for regex in self.regex_mapping.keys():
            try:
                path = re.sub(
                    regex,
                    self.regex_mapping[regex],
                    path
                )
            except Exception as e:
                self.logger.error('failed to apply regex {0} to path: {1}: {2}'.format(regex, path, e))
                continue
        return path

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

    def _replace_uid_with_singular_or_custom_mapping(self, previous_part, part):
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
        mapping = self.mapping.get(previous_part, None)
        if mapping:
            return mapping
        # ignore if previous part is version as in /v3/<project_id>/...
        if common.is_version_string(previous_part):
            return None
        # replace plural ending with 'ies' by singular ending with 'y'
        if common.is_uid_string(part):
            if previous_part.endswith('ies'):
                return previous_part.rstrip('ies') + 'y'
            return previous_part.rstrip('s')
        return None


class SwiftTargetTypeURIStrategy(TargetTypeURIStrategy):
    """
    determines the target_type_uri from a swift (object-store) request

    path of swift request might look like:  ../AUTH_accountname/containername/objectname
    and the corresponding target_type_uri like: <prefix>/account/container/object
    """
    def __init__(self):
        super(SwiftTargetTypeURIStrategy, self).__init__(name='swift', prefix='service/storage/object')

    def determine_target_type_uri(self, req):
        """
        :param req: the swift request
        :return: the target_type_uri or taxonomy.UNKNOWN
        """
        target_type_uri = []
        try:
            path = req.path
            if path.endswith('/info'):
                target_type_uri.append('info')
                return
            if path.endswith('/endpoints'):
                target_type_uri.append('endpoints')
                return

            account_id, container_id, object_id = common.get_swift_account_container_object_id_from_path(path)
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


class NovaTargetTypeURIStrategy(TargetTypeURIStrategy):
    """
    determines the target_type_uri of a nova (compute) request
    """
    def __init__(self):
        mapping = {
            # ../os-floating-ip-dns/<domain_uid>/.. => ../os-floating-ip-dns/domain/..
            'os-floating-ip-dns': 'domain',
            # ../os-floating-ip/<uid>/.. => ../os-floating-ip/floating-ip/..
            'os-floating-ips': 'floating-ip',
            'os-extra_specs': 'key',
            'os-hosts': 'host',
            'os-hypervisors': 'hypervisor',
            'os-instance-actions': 'instance-action',
            'os-keypairs': 'keypair',
            'os-networks': 'network',
            'os-security-group-rules': 'rule',
            'os-security-groups': 'security-group',
            'os-simple-tenant-usage': 'tenant',
            'os-volume_attachments': 'attachment',
            'entries': 'entry'
        }
        regex_mapping = {
            'flavors/[^/|$]+': 'flavors/flavor',
        }
        super(NovaTargetTypeURIStrategy, self).__init__(
            name='nova',
            prefix='service/compute',
            mapping=mapping,
            regex_mapping=regex_mapping
        )


class GlanceTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        mapping = {
            'shared-images': 'member',
            'members': 'member',
            'tags': 'tag',
        }
        regex_mapping = {
            'images/[^/|$]+': 'images/image',
        }
        super(GlanceTargetTypeURIStrategy, self).__init__(
            name='glance',
            prefix='service/storage/image',
            mapping=mapping,
            regex_mapping=regex_mapping
        )


class CinderTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        mapping = {
            'extra_specs': 'key',
            'encryption': 'key',
            'metadata': 'key',
            'os-volume-transfer': 'transfer',
            'capabilities': 'host',
            'group_snapshots': 'snapshot',
            'group_types': 'type',
            'group_specs': 'spec',
            'os-hosts': 'host',
            'qos-specs': 'spec',
            'os-quota-class-sets': 'class',
            'os-quota-sets': 'quota',
        }
        super(CinderTargetTypeURIStrategy, self).__init__(
            name='cinder',
            prefix='service/storage/block',
            mapping=mapping
        )


class NeutronTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        mapping = {
            'service_profiles': 'profile',
            'service-provider': 'provider',
            'metering-labels': 'label',
            'metering-label-rules': 'rule',
            'network-ip-availabilities': 'availability',
            'bandwidth_limit_rules': 'rule',
            'dscp_marking_rules': 'rule',
            'minimum_bandwidth_rules': 'rule',
            'rule-types': 'type',
        }
        regex_mapping = {
            'v(?:\d+\.)?(?:\d+\.)?(\*|\d+)/\S+/\S+/tags$': 'resource_type/resource/tags',
            'v(?:\d+\.)?(?:\d+\.)?(\*|\d+)/\S+/\S+/tags/\S+(\/+?|$)': 'resource_type/resource/tags/tag'
        }
        super(NeutronTargetTypeURIStrategy, self).__init__(
            name='nova',
            prefix='service/network',
            mapping=mapping,
            regex_mapping=regex_mapping,
        )


class DesignateTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        mapping = {
            'floatingips': 'region/floatingip'
        }

        super(DesignateTargetTypeURIStrategy, self).__init__(
            name='designate',
            prefix='service/dns',
            mapping=mapping
        )


class KeystoneTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        regex_mapping = {
            'domains/config/[0-9a-zA-Z_]+/default$': 'domains/config/group/default',
            'domains/config/[0-9a-zA-Z_]+/[0-9a-zA-Z_]+/default$': 'domains/config/group/option/default',
            'domains/\S+/config/[0-9a-zA-Z_]+/[0-9a-zA-Z_]+$': 'domains/domain/config/group/option',
            'domains/\S+/config/[0-9a-zA-Z_]+$': 'domains/domain/config/group',
            'domains/[^/]*$': 'domains/domain',
            'regions/[^/]*$': 'regions/region',
            'projects/[^/]*$': 'projects/project',
            'projects/[0-9a-zA-Z_]+/tags/[^/]*$': 'projects/project/tags/tag',
            'users/[^/]*$': 'users/user',
            'groups/[^/]*$': 'groups/group',
        }
        super(KeystoneTargetTypeURIStrategy, self).__init__(
            name='keystone',
            prefix='service/identity',
            regex_mapping=regex_mapping
        )


class ManilaTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        mapping = {
            'metadata': 'key',
            'os-share-unmanage': 'share'
        }
        regex_mapping = {
            'shares/(?!detail)[^/|$]+': 'shares/share',
            'share-groups/[^/|$]+': 'share-groups/share-group',
            'share-instances/[^/|$]+': 'share-instances/share-instance',
            'share-group-types/[^/|$]+': 'share-group-types/share-group-type',
            'os-share-unmanage/[^/|$]+': 'os-share-unmanage/share',
            'security-services/[^/|$]+': 'security-services/security-service',
            'extra_specs/[^/|$]+': 'extra_specs/key',
            'export_locations/[^/|$]+': 'export_locations/export_location'
        }
        super(ManilaTargetTypeURIStrategy, self).__init__(
            name='manila',
            prefix='service/storage/share',
            mapping=mapping,
            regex_mapping=regex_mapping
        )


class IronicTargetTypeURIStrategy(TargetTypeURIStrategy):
    def __init__(self):
        regex_mapping = {
            'nodes/[^/]+': 'nodes/node',
            'drivers/[^/]+': 'drivers/driver',
            'heartbeat/[^/]+': 'heartbeat/node',
            'bios/[^/]+': 'bios/setting',
            'traits/[^/]+': 'traits/trait',
            'vifs/[^/]+': 'vifs/vif',
            'portgroups/[^/]+': 'portgroups/portgroup',
            'ports/[^/]+': 'ports/port',
            'connectors/[^/]+': 'connectors/connector',
            'chassis/[^/]+': 'chassis/chassis',
        }
        super(IronicTargetTypeURIStrategy, self).__init__(
            name='ironic',
            prefix='service/compute/baremetal',
            regex_mapping=regex_mapping
        )
