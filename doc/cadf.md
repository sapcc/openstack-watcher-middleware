## Cloud Auditing Data Federation (CADF)

The Cloud Audit Data Federation (CADF) specification defines a model for events within the OpenStack platform.
A comprehensive overview of OpenStack requests and their CADF representation can be found here: [Cloud Audit Data Federation - OpenStack Profile (CADF-OpenStack)](https://www.dmtf.org/sites/default/files/standards/documents/DSP2038_1.1.0.pdf).  
The openstack-watcher-middleware follows DMTF specification DSP2038, version 1.1.0 as of 27 April 2015.

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


#### CADF actions

Actions characterize the operation performed by the initiator of a request against a target. 
A comprehensive definition of these actions is provided by the CADF specification mentioned above.
The watcher is capable of classifying request actions based on the HTTP method and path as follows:
```
|---------------|-------------------|-------------------|
| HTTP method   | Path              | Action            |
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

Moreover, any request path ending with a configured `path_keyword` will be interpreted as a `read/list`.  
Using this mapping the watcher is capable of classifying request actions correctly in most cases.  
However, some cases require a different mapping to alternative actions.
The default classification can be overwritten using a custom_actions mapping
  
An example for swift (object-store) looks like this:
```yaml
custom_actions:
  account:
    - method:       GET
      action_type:  read/list
    - method:       POST
      action_type:  update

    - container:
        - method:       GET
          action_type:  read/list
        - method:       POST
          action_type:  update

        - object:
            - method:       POST
              action_type:  update
```
This configuration results in the following mapping:
```
|---------------|-----------------------------------|-------------------|
| HTTP method   | Path                              | Action            |
|---------------|-----------------------------------|-------------------|
| GET           | ../v1/account                     | read/list         |
| POST          | ../v1/account                     | update            |
| GET           | ../v1/account/container           | read/list         |
| POST          | ../v1/account/container           | update            | 
| POST          | ../v1/account/container/object    | update            |
| ...           |                                   |                   |
|---------------|-----------------------------------|-------------------|    
````

#### Action requests

Some requests may use `POST` or `PUT` with a path including `/action` or `/os-instance-actions` and a json body to perform an action on a resource.
In which case the middleware evaluates the request body to determine the action.
The default mapping will return a CADF action in the following format: `update/<action>`.
A `os-` prefix will be trimmed from the action.  

Example: Nova (compute) add security group to an instance and reset state
````
|---------------|-----------------------------------|-------------------------------------------|---------------------------|
| HTTP method   | Path                              | JSON body                                 | CADF action               |
|---------------|-----------------------------------|-------------------------------------------|---------------------------|
| POST          | /servers/{server_id}/action       | { "addSecurityGroup": { "name": "test" }} | update/addSecurityGroup   |
| POST          | /servers/{server_id}/action       | { "os-resetState": { "state": "active" }} | update/os-resetState      |
| ...           | ...                               |                                           |                           |
|---------------|-----------------------------------|-------------------------------------------|---------------------------|
````
  
The default behaviour can be overwritten by via the custom actions configuration as shown below.
```
custom_actions:
  servers:
    server:
      action:
        - <original_action>: <custom_cadf_action>
        - addSecurityGroup: update/addSecurityGroup
        - os-resetState: update/os-resetState
```

#### CADF target type URI

The *target type URI* is a CADF specific representation of the request's target URI consisting of
a service-specific prefix and the target URI without version or UUID strings. 

In most cases this middleware builds the target type URI by concatenating the `service/<service_type>` prefix and
all parts of the target URI which do not contain a UUID.
In case a UUID is found, it's substituted by the singular of the previous part.  
Should this default behaviour not suffice, writing a [custom strategy](./watcher/target_type_uri_strategy.py) might be required.

Examples:
```
|-------------|-------------------------------------------------|-----------------------------------------------|
| Service     | Target URI                                      | CADF Target Type URI                          |
|-------------|-------------------------------------------------|-----------------------------------------------|
| compute     | /servers/{server_uuid}/action                   | service/compute/servers/server/action         |
| dns         | /v2/zones/{zone_id}/recordsets/{recordset_id}   | service/dns/zones/zone/recordsets/recordset   |
| ...         | ...                                             | ...                                           |
|-------------|-------------------------------------------------|-----------------------------------------------|
```


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
