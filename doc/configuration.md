### WSGI configuration

Configuration options in the paste.ini as shown below
```yaml
[filter:watcher]
use = egg:watcher-middleware#watcher
# service_type as defined in service catalog. See supported services.
# example: object-store, compute, dns, etc.
service_type = <service_type>
```
Optional settings:
```yaml
# path to configuration file containing customized action definitions
config_file = /etc/watcher.yaml

# project id can be determined from either request path or service catalog if keystone.auth_token middleware is set to 'include_service_catalog = true'
# determine the project id from request path
project_id_from_path = true | false (default)

# determine the project id from the service catalog
project_id_from_service_catalog = true | false (default)

# whether to include the target project id in the openstack_watcher_* metrics
include_target_project_id_in_metric = true (default) | false

# whether to include the initiators user id in the openstack_watcher_* metrics
include_initiator_user_id_in_metric = true | false (default)

# per default the target.type_uri is prefixed by 'service/<service_type>/'
# if the cadf spec. requires a different prefix, it might be given here 
# example: swift (object-store)
# service_type = object-store
# cadf_service_name = service/storage/object
cadf_service_name = <service_name>

# metrics are emitted via StatsD
statsd_host = 127.0.0.1
statsd_port = 9125
statsd_namespace = openstack_watcher
```

#### Configuration file

Additionally, the watcher might require a configuration file.  
For existing services these can be found in the [examples](./etc).
More details are provided [here](./doc/cadf.md)

The following snippet provides an overview of configuration options for a service.
```yaml
# keywords in a request path are followed by the UUID or name of a resource.
# in the target type URI the UUID or name of a resource is replaced by the singular of the keyword.
# a custom value for the singular can also be provided by a mapping <plural>:<singular>
# moreover, if a path ends with a keyword the action will be 'read/list'
path_keywords:
    - users
    - tokens
    - availability-zones: zone
    ..

# per default every word following a path keyword is replaced. 
# however, exclusions can be configured by this list 
path_exclusions:
    - OS-PKI
    - ..

# some request path' are quite hard to map to their target type URI as the replacements can't be derived from the previous part.
# thus, in some cases providing a mapping of <path_regex>: <target_type_URI> might be inevitable
# note: the complete path (including versions, etc. ) needs to be reflected in the regex 
regex_path_mapping:
  - '\S+/domains/config/[0-9a-zA-Z_]+/default$': 'domains/config/group/default'

# CADF actions are determined by the request method and their path as outlined in the table in the CADF section of this documentation
# however, these can be overwritten using the target type URI and the request method with a custom action_type
custom_actions:
  tokens:
    - token:
        - method: GET
          action_type: custom_action
```
