# Prometheus Flask exporter

[![PyPI](https://img.shields.io/pypi/v/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![PyPI](https://img.shields.io/pypi/pyversions/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/prometheus-flask-exporter.svg)](https://pypi.python.org/pypi/prometheus-flask-exporter)
[![Coverage Status](https://coveralls.io/repos/github/rycus86/prometheus_flask_exporter/badge.svg?branch=master)](https://coveralls.io/github/rycus86/prometheus_flask_exporter?branch=master)
[![Code Climate](https://codeclimate.com/github/rycus86/prometheus_flask_exporter/badges/gpa.svg)](https://codeclimate.com/github/rycus86/prometheus_flask_exporter)
[![Test & publish package](https://github.com/rycus86/prometheus_flask_exporter/actions/workflows/test-and-publish.yml/badge.svg)](https://github.com/rycus86/prometheus_flask_exporter/actions/workflows/test-and-publish.yml)

This library provides HTTP request metrics to export into
[Prometheus](https://prometheus.io/).
It can also track method invocations using convenient functions.

## Installing

Install using [PIP](https://pip.pypa.io/en/stable/quickstart/):

```bash
pip install prometheus-flask-exporter
```
or paste it into requirements.txt:
```
# newest version
prometheus-flask-exporter

# or with specific version number
prometheus-flask-exporter==0.23.2
```
and then install dependencies from requirements.txt file as usual:
```
pip install -r requirements.txt
```


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
- `flask_http_request_exceptions_total` (Counter)
  Labels: `method` and `status`.
  Total number of uncaught exceptions when serving Flask requests.
- `flask_exporter_info` (Gauge)
  Information about the Prometheus Flask exporter itself (e.g. `version`).

The prefix for the default metrics can be controlled by the `defaults_prefix` parameter.
If you don't want to use any prefix, pass the `prometheus_flask_exporter.NO_PREFIX` value in.
The buckets on the default request latency histogram can be changed by the `buckets` parameter, and if using a summary for them is more appropriate for your use case, then use the `default_latency_as_histogram=False` parameter.

To register your own *default* metrics that will track all registered
Flask view functions, use the `register_default` function.

```python
app = Flask(__name__)
metrics = PrometheusMetrics(app)

@app.route('/simple')
def simple_get():
    pass
    
metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)
```

*Note:* register your default metrics after all routes have been set up.
Also note, that Gauge metrics registered as default will track the
`/metrics` endpoint, and this can't be disabled at the moment.

If you want to apply the same metric to multiple (but not all) endpoints,
create its wrapper first, then add to each function.

```python
app = Flask(__name__)
metrics = PrometheusMetrics(app)

by_path_counter = metrics.counter(
    'by_path_counter', 'Request count by request paths',
    labels={'path': lambda: request.path}
)

@app.route('/simple')
@by_path_counter
def simple_get():
    pass
    
@app.route('/plain')
@by_path_counter
def plain():
    pass
    
@app.route('/not/tracked/by/path')
def not_tracked_by_path():
    pass
```

You can avoid recording metrics on individual endpoints
by decorating them with `@metrics.do_not_track()`, or use the 
`excluded_paths` argument when creating the `PrometheusMetrics` instance
that takes a regular expression (either a single string, or a list) and
matching paths will be excluded. These apply to both built-in and user-defined
default metrics, unless you disable it by setting the `exclude_user_defaults`
argument to `False`. If you have functions that are inherited or otherwise get
metrics collected that you don't want, you can use `@metrics.exclude_all_metrics()`
to exclude both default and non-default metrics being collected from it.

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

You can also set default labels to add to every request managed by
a `PrometheusMetrics` instance, using the `default_labels` argument.
This needs to be a dictionary, where each key will become a metric
label name, and the values the label values.
These can be constant values, or dynamic functions, see below in the
[Labels](#Labels) section.

> The `static_labels` argument is deprecated since 0.15.0,
> please use the new `default_labels` argument.

If you use another framework over Flask (perhaps
[Connexion](https://connexion.readthedocs.io/)) then you might return
responses from your endpoints that Flask can't deal with by default.
If that is the case, you might need to pass in a `response_converter`
that takes the returned object and should convert that to a Flask
friendly response.
See `ConnexionPrometheusMetrics` for an example.

## Labels

When defining labels for metrics on functions,
the following values are supported in the dictionary:

- A simple static value
- A no-argument callable
- A single argument callable that will receive the Flask response
  as the argument

Label values are evaluated within the request context.

## Initial metric values
_For more info see: https://github.com/prometheus/client_python#labels_

Metrics without any labels will get an initial value.
Metrics that only have static-value labels will also have an initial value. (except when they are created with the option `initial_value_when_only_static_labels=False`)
Metrics that have one or more callable-value labels will not have an initial value.

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

This library also supports the Flask [app factory pattern](http://flask.pocoo.org/docs/1.0/patterns/appfactories/). Use the `init_app` method to attach the library to one or more application objects. Note, that to use this mode, you'll need to use the `for_app_factory()` class method to create the `metrics` instance, or pass in `None` for the `app` in the constructor.

```python
metrics = PrometheusMetrics.for_app_factory()
# then later:
metrics.init_app(app)
```
**NOTE**: When using the Flask application in debug mode, you must set the `DEBUG_METRICS` environment variable to `1` before starting the application to ensure the `/metrics` endpoint is exposed:

```bash
export DEBUG_METRICS=1
```
This step is crucial because, without it, the `/metrics` endpoint might not be properly registered and displayed in debug mode.

## Securing the metrics endpoint

If you wish to have authentication (or any other special handling) on the metrics endpoint,
you can use the `metrics_decorator` argument when creating the `PrometheusMetrics` instance.
For example to integrate with [Flask-HTTPAuth](https://github.com/miguelgrinberg/Flask-HTTPAuth)
use it like it's shown in the example below.

```python
app = Flask(__name__)
auth = HTTPBasicAuth()
metrics = PrometheusMetrics(app, metrics_decorator=auth.login_required)

# ... other authentication setup like @auth.verify_password below
```

See a full example in the [examples/flask-httpauth](https://github.com/rycus86/prometheus_flask_exporter/tree/master/examples/flask-httpauth) folder.

## Custom metrics endpoint

You can also take full control of the metrics endpoint by generating its contents,
and managing how it is exposed by yourself.

```python
app = Flask(__name__)
# path=None to avoid registering a /metrics endpoint on the same Flask app
metrics = PrometheusMetrics(app, path=None)

# later ... generate the response (and its content type) to expose to Prometheus
response_data, content_type = metrics.generate_metrics()
```

See the related conversation in [issue #135](https://github.com/rycus86/prometheus_flask_exporter/issues/135).

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

Also see the `GunicornInternalPrometheusMetrics` class if you want to have
the metrics HTTP endpoint exposed internally, on the same Flask application.

```python
# an extension targeted at Gunicorn deployments with an internal metrics endpoint
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

app = Flask(__name__)
metrics = GunicornInternalPrometheusMetrics(app)

# then in the Gunicorn config file:
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

def child_exit(server, worker):
    GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
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

An additional Flask extension for apps with `processes=N` and `threaded=False` exists
with the `MultiprocessInternalPrometheusMetrics` class.

```python
from flask import Flask
from prometheus_flask_exporter.multiprocess import MultiprocessInternalPrometheusMetrics

app = Flask(__name__)
metrics = MultiprocessInternalPrometheusMetrics(app)

...

if __name__ == '__main__':
    app.run('0.0.0.0', 4000, processes=5, threaded=False)
```

__Note:__ this needs the `PROMETHEUS_MULTIPROC_DIR` environment variable
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

### uWSGI lazy-apps

When [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) is configured 
to run with [lazy-apps]([lazy-apps](https://uwsgi-docs.readthedocs.io/en/latest/articles/TheArtOfGracefulReloading.html#preforking-vs-lazy-apps-vs-lazy)),
exposing the metrics endpoint on a separate HTTP server (and port) is not functioning yet.
A workaround is to register the endpoint on the main Flask application.

```python
app = Flask(__name__)
metrics = UWsgiPrometheusMetrics(app)
metrics.register_endpoint('/metrics')
# instead of metrics.start_http_server(port)
```

See [#31](https://github.com/rycus86/prometheus_flask_exporter/issues/31)
for context, and please let me know if you know a better way!

## Connexion integration

The [Connexion](https://connexion.readthedocs.io/) library has some
support to automatically deal with certain response types, for example
dataclasses, which a plain Flask application would not accept.
To ease the integration, you can use `ConnexionPrometheusMetrics` in
place of `PrometheusMetrics` that has the `response_converter` set
appropriately to be able to deal with whatever Connexion supports for
Flask integrations.

```python
import connexion
from prometheus_flask_exporter import ConnexionPrometheusMetrics

app = connexion.App(__name__)
metrics = ConnexionPrometheusMetrics(app)
```

See a working sample app in the `examples` folder, and also the
[prometheus_flask_exporter#61](https://github.com/rycus86/prometheus_flask_exporter/issues/61) issue. 

There's a caveat about this integration, where any endpoints that
do not return JSON responses need to be decorated with
`@metrics.content_type('...')` as this integration would force them
to be `application/json` otherwise.

```python
metrics = ConnexionPrometheusMetrics(app)

@metrics.content_type('text/plain')
def plain_response():
    return 'plain text'
```

See the [prometheus_flask_exporter#64](https://github.com/rycus86/prometheus_flask_exporter/issues/64) issue for more details.

## Flask-RESTful integration

The [Flask-RESTful library](https://flask-restful.readthedocs.io/) has
some custom response handling logic, which can be helpful in some cases.
For example, returning `None` would fail on plain Flask, but it
works on Flask-RESTful.
To ease the integration, you can use `RESTfulPrometheusMetrics` in
place of `PrometheusMetrics` that sets the `response_converter` to use
the Flask-RESTful `API` response utilities.

```python
from flask import Flask
from flask_restful import Api
from prometheus_flask_exporter import RESTfulPrometheusMetrics

app = Flask(__name__)
restful_api = Api(app)
metrics = RESTfulPrometheusMetrics(app, restful_api)
```

See a working sample app in the `examples` folder, and also the
[prometheus_flask_exporter#62](https://github.com/rycus86/prometheus_flask_exporter/issues/62) issue.

## License

MIT
