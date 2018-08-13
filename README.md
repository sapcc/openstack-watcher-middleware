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
More information is provided in the [CADF documentation](./doc/cadf.md).

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
| Barbican              | key-manager           |
| Cinder                | volume                | 
| Designate             | dns                   |
| Glance                | image                 | 
| Ironic                | baremetal             |
| Keystone              | identity              |
| Manila                | share                 |
| Neutron               | network               |
| Nova                  | compute               |
| Swift                 | object-store          |
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

### Configuration

Mandatory configuration options in the paste.ini as shown below. See the [configuration section](./doc/configuration.md) for more options.
```yaml
[filter:watcher]
use = egg:watcher-middleware#watcher
# service_type as defined in service catalog. See supported services.
# example: object-store, compute, dns, etc.
service_type = <service_type>

# path to configuration file containing customized action definitions
config_file = /etc/watcher.yaml
```
