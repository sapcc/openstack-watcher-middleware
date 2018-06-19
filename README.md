OpenStack Watcher Middleware
===============================

The OpenStack Watcher is a WSGI middleware capable of analyzing OpenStack traffic and classifying according to the CADF Specification outlined further below.

## Features

- Analyzes OpenStack requests
- Classifies requests according to [DMTF CADF specification](https://www.dmtf.org/standards/cadf).
- Stores classification data in GCI environment, which is passed to subsequent WSGI middlewares for further evaluation
- Exposes Prometheus metrics

## Principles

The watcher distinguishes between `initiator` and `target` of an action. 
`Initiator` describes the resource or the user that starts the request, ` Target` refers to the resource against which the action was performed.

### CADF Specification

Requests are classified according to the CADF specification.
A comprehensive list of of OpenStack requests and their CADF representation can be found here: [Cloud Audit Data Federation - OpenStack Profile (CADF-OpenStack)](https://www.dmtf.org/sites/default/files/standards/documents/DSP2038_1.1.0.pdf).  
This middleware follows DMTF specification DSP2038, version 1.1.0 as of 27 April 2015.

### Classification

The watcher classifies requests and records the following attributes.
These are emitted as Prometheus metrics and passed in the GCI environment with the `WATCHER` prefix and in capital letters.
For example: `WATCHER.ACTION`, `WATCHER.INITIATOR_PROJECT_ID`, `WATCHER.TARGET_PROJECT_ID`, etc. .

- `action`:       the CADF action
- `service`:      the name of the service

**Initiator** attributes:
- `project_id`:   the initiators project uid. `None` if domain scoped, `Unknown` if not authenticated.
- `domain_id`:    the initiators domain uid. `None` if project scoped, `Unknown` if not authenticated.
- `user_id`:      the initiators user id. `Unknown` if not authenticated.
- `client_addr`:  the initiators client address
  
  
**Target** attributes:
- `project_id`:   the targets project uid. `Unknown` if it could not be determined. 
- `type_uri`:     characterizes the URI of the target resource


**Additional service specific attributes**:

- Swift (object-store):
    - `target.container_id`: the name/id of the swift container. `None` if not relevant. `Unknown` if it could not be determined.
    

#### Determine target project 

Determining the target of an operation can be hard. The watcher offers 3 mutually exclusive approaches to that:   
1. Extract target project id from token.
Assumptions: Initiator is authenticated. Initiator and target are in the same project.
In which case the initiator.project_id as seen in the keystone token will be equal to the target.project_id. 
While this may be correct in most cases, if the services policy allows cross-project operations, one of the following approaches is suggested.

2. Extract target project id from request path.  
Assumptions: Initiator may be anonymous (not authenticated). The request path contains the project id.  
For example swift (object-store) requests might contain the uid of the target project id in the format `../<version>/AUTH_<target_project_id>/..`
This does not allow conclusions on the initiator, but on the target. 

3. Extract target project id from service catalog.
Assumption: Initiator is authenticated. The token is scoped to the target project and its service catalog contains endpoint(s) for the relevant service 
that include the project id in the format `http(s)://<service>:<port>/<version>/<target_project_id>`.
This requires `include_service_catalog = true` in the keystone.auth_token middleware and does not work when unauthenticated requests are allowed.
See section [keystone auth_token middleware](#keystone-auth_token-middleware). 
 
### CADF actions

Actions characterize the operation performed by the initiator of a request against a target. 
A comprehensive definition of these actions is provided by the CADF specification mentioned above.
The watcher is capable of classifying request actions based on the HTTP method and path as follows:
```
|---------------|-------------------|-------------------|
| HTTP method   | path              | action            |
|---------------|-------------------|-------------------|
| GET           |                   | read              |
| GET           | ../detail         | read/list         | 
| HEAD          |                   | read              |
| PUT           |                   | update            |
| PATCH         |                   | update            |
| POST          |                   | create            |
| POST          | ../auth/tokens    | authenticate      |
| DELETE        |                   | delete            |
| COPY          |                   | create/copy       |
|---------------|-------------------|-------------------|        
```

Using this mapping the watcher is capable of classifying request actions correctly in most cases.  
However, some cases require a different mapping to alternative actions.
The default classification can be overwritten using a custom_actions mapping
  
An example for swift (object-store) looks like this:
```yaml
custom_actions:
  account:
    - method: GET
      action: 'read/list'
    - method: POST
      action: 'update'

    - container:
        - method: GET
          action: 'read/list'
        - method: POST
          action: 'update'

        - object:
            - method: POST
              action: 'update'
```
This configuration results in the following mapping:
```
|---------------|-----------------------------------|-------------------|
| HTTP method   | path                              | action            |
|---------------|-----------------------------------|-------------------|
| GET           | ../v1/account                     | read/list         |
| POST          | ../v1/account                     | update            |
| GET           | ../v1/account/container           | read/list         |
| POST          | ../v1/account/container           | update            | 
| POST          | ../v1/account/container/object    | update            |
| ...           |                                   |                   |
|---------------|-----------------------------------|-------------------|    
````

## Supported Services

This middleware currently provides CADF-compliant support for the following OpenStack services:

- Cinder (Block storage)
- Designate (DNS)
- Glance (Image)
- Neutron (Network)
- Nova (Compute)
- Swift (Object store)

Configurations for these services are provided [here](./etc) 
Support for additional OpenStack services might require additional action configurations.

## Installation & Usage

Install via
```
pip install git+https://github.com/sapcc/openstack-watcher-middleware.git 
```

### Keystone auth_token middleware

The watcher determines the initiator of an action via its keystone token,
thus the middleware needs to be added *after* the [keystone.auth_token middleware](https://docs.openstack.org/keystone/queens/admin/identity-auth-token-middleware.html).  
Setting `include_service_catalog = true` includes the service catalog on token validation, 
which enables the watcher to determine the target project id for a service based on the endpoint(s) found in this scoped catalog.

**Note**:
Setting`delay_auth_decision = true`, configures the auth_token middleware to delegate the authorization decision to downstream WSGI components.
This enables unauthenticated requests, hence the initators project, domain and user uid *cannot* be determined via the keystone token and are `Unknown`.
In which case the initiator can only be characterized by its client address.
Furthermore, the *target.project_id* cannot be extracted from the token nor the service catalog.
If the request path does not include the target.project_id, it will be `Unknown`. 

### Pipeline 

The watcher should be added after the auth_token middleware.
```
pipeline = .. auth_token watcher ..
```

### Watcher configuration
and configure by adding the following snippet to the paste.ini:
```yaml
[filter:watcher]
use = egg:watcher-middleware#watcher
# service_type as defined in service catalog
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

# per default the target.type_uri is prefixed by 'service/<service_type>/'.
# if the cadf spec. requires a different prefix, it might be given here 
# example: swift (object-store)
# service_type = object-store would result in 'service/object-store/', but cadf requires 'service/storage/object/',
# so one needs to set cadf_service_name = service/storage/object
cadf_service_name = <service_name>

# metrics are emitted via StatsD
statsd_host = 127.0.0.1
statsd_port = 9125
statsd_namespace = openstack_watcher
```
