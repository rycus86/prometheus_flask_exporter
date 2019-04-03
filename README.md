# Prometheus Flask exporter

[![PyPI](https://img.shields.io/pypi/v/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![PyPI](https://img.shields.io/pypi/pyversions/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![Travis](https://img.shields.io/travis/rycus86/prometheus_flask_exporter.svg)](https://travis-ci.org/rycus86/prometheus_flask_exporter)
[![Coverage Status](https://coveralls.io/repos/github/rycus86/prometheus_flask_exporter/badge.svg?branch=master)](https://coveralls.io/github/rycus86/prometheus_flask_exporter?branch=master)
[![Code Climate](https://codeclimate.com/github/rycus86/prometheus_flask_exporter/badges/gpa.svg)](https://codeclimate.com/github/rycus86/prometheus_flask_exporter)

This library provides HTTP request metrics to export into
[Prometheus](https://prometheus.io/).
It can also track method invocations using convenient functions.

## Usage

```python
from flask import Flask, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# static information as metric
metrics.info('app_info', 'Application info', version='1.0.3')

@app.route('/')
def main():
    pass  # requests tracked by default

@app.route('/skip')
@metrics.do_not_track()
def skip():
    pass  # default metrics are not collected

@app.route('/<item_type>')
@metrics.do_not_track()
@metrics.counter('invocation_by_type', 'Number of invocations by type',
         labels={'item_type': lambda: request.view_args['type']})
def by_type(item_type):
    pass  # only the counter is collected, not the default metrics

@app.route('/long-running')
@metrics.gauge('in_progress', 'Long running requests in progress')
def long_running():
    pass

@app.route('/status/<int:status>')
@metrics.do_not_track()
@metrics.summary('requests_by_status', 'Request latencies by status',
                 labels={'status': lambda r: r.status_code})
@metrics.histogram('requests_by_status_and_path', 'Request latencies by status and path',
                   labels={'status': lambda r: r.status_code, 'path': lambda: request.path})
def echo_status(status):
    return 'Status: %s' % status, status
```

## Default metrics

The following metrics are exported by default
(unless the `export_defaults` is set to `False`).

- `flask_http_request_duration_seconds` (Histogram)
  Labels: `method`, `path` and `status`.
  Flask HTTP request duration in seconds for all Flask requests.
- `flask_http_request_total` (Counter)
  Labels: `method` and `status`.
  Total number of HTTP requests for all Flask requests.
- `flask_exporter_info` (Gauge)
  Information about the Prometheus Flask exporter itself (e.g. `version`).

The prefix for the default metrics can be controlled by the `defaults_prefix` parameter.
Is you don't want to use any prefix, pass the `prometheus_flask_exporter.NO_PREFIX` value in.

## Configuration

By default, the metrics are exposed on the same Flask application on the
`/metrics` endpoint and using the core Prometheus registry.
If this doesn't suit your needs, set the `path` argument to `None` and/or
the `export_defaults` argument to `False` plus change the `registry`
argument if needed.

The `group_by` constructor argument controls what
the default request duration metric is tracked by: endpoint (function)
instead of URI path (the default). This parameter also accepts a function
to extract the value from the request, or a name of a property of the request object.
Examples:

```python
PrometheusMetrics(app, group_by='path')         # the default
PrometheusMetrics(app, group_by='endpoint')     # by endpoint
PrometheusMetrics(app, group_by='url_rule')     # by URL rule

def custom_rule(req):  # the Flask request object
    """ The name of the function becomes the label name. """
    return '%s::%s' % (req.method, req.path)

PrometheusMetrics(app, group_by=custom_rule)    # by a function

# Error: this is not supported:
PrometheusMetrics(app, group_by=lambda r: r.path)
```

> The `group_by_endpoint` argument is deprecated since 0.4.0,
> please use the new `group_by` argument.

The `register_endpoint` allows exposing the metrics endpoint on a specific path.
It also allows passing in a Flask application to register it on but defaults
to the main one if not defined.

Similarly, the `start_http_server` allows exposing the endpoint on an
independent Flask application on a selected HTTP port.
It also supports overriding the endpoint's path and the HTTP listen address.

## Labels

When defining labels for metrics on functions,
the following values are supported in the dictionary:

- A simple static value
- A no-argument callable
- A single argument callable that will receive the Flask response
  as the argument

Label values are evaluated within the request context.

## Application information

The `PrometheusMetrics.info(..)` method provides a way to expose
information as a `Gauge` metric, the application version for example.

The metric is returned from the method to allow changing its value
from the default `1`:

```python
metrics = PrometheusMetrics(app)
info = metrics.info('dynamic_info', 'Something dynamic')
...
info.set(42.1)
```

## Examples

See some simple examples visualized on a Grafana dashboard by running
the demo in the [examples/sample-signals](https://github.com/rycus86/prometheus_flask_exporter/tree/master/examples/sample-signals) folder.

![Example dashboard](https://github.com/rycus86/prometheus_flask_exporter/raw/master/examples/sample-signals/dashboard.png)

## App Factory Pattern

This library also supports the flask [app factory pattern](http://flask.pocoo.org/docs/1.0/patterns/appfactories/). Use the `init_app` method to attach the library to one or more application objects. Note, that to use this mode, you'll need to pass in `None` for the `app` in the constructor.

```python
metrics = PrometheusMetrics(app=None, ...)
# then later:
metrics.init_app(app)
```

## Debug mode

Please note, that changes being live-reloaded, when running the Flask
app with `debug=True`, are not going to be reflected in the metrics.
See [https://github.com/rycus86/prometheus_flask_exporter/issues/4](https://github.com/rycus86/prometheus_flask_exporter/issues/4)
for more details.

Alternatively - since version `0.5.1` - if you set the `DEBUG_METRICS`
environment variable, you will get metrics for the latest reloaded code.
These will be exported on the main Flask app.
Serving the metrics on a different port is not going to work
most probably - e.g. `PrometheusMetrics.start_http_server(..)` is not
expected to work.

## WSGI

Getting accurate metrics for WSGI apps might require a bit more setup.
See a working sample app in the `examples` folder, and also the
[prometheus_flask_exporter#5](https://github.com/rycus86/prometheus_flask_exporter/issues/5) issue.

### Multiprocess applications

For multiprocess applications (WSGI or otherwise), you can find some
helper classes in the `prometheus_flask_exporter.multiprocess` module.
These provide convenience wrappers for exposing metrics in an
environment where multiple copies of the application will run on a single host.

```python
# an extension targeted at Gunicorn deployments
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

app = Flask(__name__)
metrics = GunicornPrometheusMetrics(app)

# then in the Gunicorn config file:
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

def when_ready(server):
    GunicornPrometheusMetrics.start_http_server_when_ready(8080)

def child_exit(server, worker):
    GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
```

There's a small wrapper available for [Gunicorn](https://gunicorn.org/) and
[uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/index.html), for everything
else you can extend the `prometheus_flask_exporter.multiprocess.MultiprocessPrometheusMetrics` class
and implement the `should_start_http_server` method at least.

```python
from prometheus_flask_exporter.multiprocess import MultiprocessPrometheusMetrics

class MyMultiprocessMetrics(MultiprocessPrometheusMetrics):
    def should_start_http_server(self):
        return this_worker() == primary_worker()
```

This should return `True` on one process only, and the underlying
[Prometheus client library](https://github.com/prometheus/client_python)
will collect the metrics for all the forked children or siblings.

__Note:__ this needs the `prometheus_multiproc_dir` environment variable
to point to a valid, writable directory.

You'll also have to call the `metrics.start_http_server()` function
explicitly somewhere, and the `should_start_http_server` takes care of
only starting it once.
The [examples](https://github.com/rycus86/prometheus_flask_exporter/tree/master/examples) folder
has some working examples on this.

Please also note, that the Prometheus client library does not collect process level
metrics, like memory, CPU and Python GC stats when multiprocessing is enabled.
See the [prometheus_flask_exporter#18](https://github.com/rycus86/prometheus_flask_exporter/issues/18)
issue for some more context and details.

A final caveat is that the metrics HTTP server will listen on __any__ paths
on the given HTTP port, not only on `/metrics`, and it is not implemented
at the moment to be able to change this.

## License

MIT
