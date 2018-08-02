OpenStack Watcher Middleware
===============================

[![Build Status](https://travis-ci.org/sapcc/openstack-watcher-middleware.svg?branch=master)](https://travis-ci.org/sapcc/openstack-watcher-middleware)

The OpenStack Watcher is a WSGI middleware capable of analyzing OpenStack traffic and classifying according to the CADF Specification outlined further below.

## Features

- Analyzes OpenStack requests
- Classifies requests according to [DMTF CADF specification](https://www.dmtf.org/standards/cadf).
- Stores classification data in GCI environment, which is passed to subsequent WSGI middlewares for further evaluation
- Exposes Prometheus metrics

## Principles

The watcher middleware classifies OpenStack requests based on the Cloud Auditing Data Federation (CADF) specification.
It distinguishes between `initiator` and `target` of an action. 
`Initiator` describes the resource or the user who sent the request, `Target` refers to the resource against which the action was performed.

### CADF Specification

The Cloud Audit Data Federation (CADF) specification defines a model for events within the OpenStack platform.
This data model is used by the watcher middleware to classify requests.
More information is provided in the [documentation](./doc/cadf.md).

#### Classification

The following attributes are recorded and passed via the WSGI environment through the pipeline.
Moreover, this meta data is emitted as Prometheus metrics.  
Note: The attributes in the environment are capitalized.
For example: `WATCHER.ACTION`, `WATCHER.INITIATOR_PROJECT_ID`, `WATCHER.TARGET_PROJECT_ID`, etc. .

- `action`:       the CADF action
- `service`:      the name of the service

**Initiator** attributes:
- `project_id`:   the initiators project uid. `None` if domain scoped, `Unknown` if not authenticated.
- `domain_id`:    the initiators domain uid. `None` if project scoped, `Unknown` if not authenticated.
- `user_id`:      the initiators user id. `Unknown` if not authenticated.
- `host_address`: the initiators host address
  
  
**Target** attributes:
- `project_id`:   the targets project uid. `Unknown` if it could not be determined. 
- `type_uri`:     characterizes the URI of the target resource


**Additional service specific attributes**:

- Swift (object-store):
    - `target.container_id`: the name/id of the swift container. `None` if not relevant. `Unknown` if it could not be determined.

### Metrics

The openstack-watcher-middleware exposes the following Prometheus metrics via statsD.

`openstack_watcher_api_requests_total`                  - total count of api requests
`openstack_watcher_api_requests_duration_seconds`       - request latency in seconds
`openstack_watcher_api_requests_duration_seconds_count` - total number of samples of the request duration metric
`openstack_watcher_api_requests_duration_seconds_sum`   - sum of request latency

## Supported Services

This middleware currently provides CADF-compliant support for the following OpenStack services:
````
|-----------------------|-----------------------|
| Service name          | Service type          |
|-----------------------|-----------------------|
| Cinder                | volume                |
| Glance                | image                 | 
| Neutron               | network               |
| Nova                  | compute               |
| Swift                 | object-store          |
| Designate             | dns                   |
| Keystone              | identity              |
| Ironic                | baremetal             |
|-----------------------|-----------------------|
````

Configurations for these services are provided [here](./etc) 
Support for additional OpenStack services might require additional action configurations.

## Installation & Usage

Install via
```
pip install git+https://github.com/sapcc/openstack-watcher-middleware.git 
```

### Pipeline 

The watcher should be added after the keystone auth_token middleware to be able to obtain information on the scope (project/domain) of the action.
```
pipeline = .. auth_token watcher ..
```

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
project_id_from_path = true | false
# determine the project id from the service catalog
project_id_from_service_catalog = true | false

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
