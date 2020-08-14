import os
import re
import sys
import inspect
import warnings
import functools
import threading
from timeit import default_timer

from flask import request, make_response, current_app
from flask import Flask, Response
from flask.views import MethodViewType
from werkzeug.serving import is_running_from_reloader
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

if sys.version_info[0:2] >= (3, 4):
    # Python v3.4+ has a built-in has __wrapped__ attribute
    wraps = functools.wraps
else:
    # in previous Python version we have to set the missing attribute
    def wraps(wrapped, assigned=functools.WRAPPER_ASSIGNMENTS,
              updated=functools.WRAPPER_UPDATES):
        def wrapper(f):
            f = functools.wraps(wrapped, assigned, updated)(f)
            f.__wrapped__ = wrapped
            return f

        return wrapper

try:
    # try to convert http.HTTPStatus to int status codes
    from http import HTTPStatus

    def _to_status_code(response_status):
        if isinstance(response_status, HTTPStatus):
            return response_status.value
        else:
            return response_status
except ImportError:
    # otherwise simply use the status as is
    def _to_status_code(response_status):
        return response_status

NO_PREFIX = '#no_prefix'
"""
Constant indicating that default metrics should not have any prefix applied.
It purposely uses invalid characters defined for metrics names as specified in Prometheus
documentation (see: https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
"""


class PrometheusMetrics(object):
    """
    Prometheus metrics export configuration for Flask.

    The default metrics include a Histogram for HTTP request latencies
    and number of HTTP requests plus a Counter for the total number
    of HTTP requests.

    Sample usage:

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

    Label values can be defined as callables:

        - With a single argument that will be the Flask Response object
        - Without an argument, possibly to use with the Flask `request` object
    """

    def __init__(self, app, path='/metrics',
                 export_defaults=True, defaults_prefix='flask',
                 group_by='path', buckets=None,
                 default_labels=None, response_converter=None,
                 excluded_paths=None, registry=None, **kwargs):
        """
        Create a new Prometheus metrics export configuration.

        :param app: the Flask application
        :param path: the metrics path (defaults to `/metrics`)
        :param export_defaults: expose all HTTP request latencies
            and number of HTTP requests
        :param defaults_prefix: string to prefix the default exported
            metrics name with (when either `export_defaults=True` or
            `export_defaults(..)` is called) or in case you don't want
            any prefix then use `NO_PREFIX` constant
        :param group_by: group default HTTP metrics by
            this request property, like `path`, `endpoint`, `url_rule`, etc.
            (defaults to `path`)
        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param default_labels: default labels to attach to each of the
            metrics exposed by this `PrometheusMetrics` instance
        :param response_converter: a function that converts the captured
            the produced response object to a Flask friendly representation
        :param excluded_paths: regular expression(s) as a string or
            a list of strings for paths to exclude from tracking
        :param registry: the Prometheus Registry to use
        """

        self.app = app
        self.path = path
        self._export_defaults = export_defaults
        self._defaults_prefix = defaults_prefix or 'flask'
        self._default_labels = default_labels or {}
        self._response_converter = response_converter or make_response
        self.buckets = buckets
        self.version = __version__

        if registry:
            self.registry = registry
        else:
            # load the default registry from the underlying
            # Prometheus library here for easier unit testing
            # see https://github.com/rycus86/prometheus_flask_exporter/pull/20
            from prometheus_client import REGISTRY as DEFAULT_REGISTRY
            self.registry = DEFAULT_REGISTRY

        if kwargs.get('static_labels'):
            warnings.warn(
                'The `static_labels` argument of `PrometheusMetrics` is '
                'deprecated since 0.15.0, please use the '
                'new `default_labels` argument.', DeprecationWarning
            )

            for key, value in kwargs.get('static_labels', dict()).items():
                if key not in self._default_labels:
                    self._default_labels[key] = value

        if kwargs.get('group_by_endpoint') is True:
            warnings.warn(
                'The `group_by_endpoint` argument of `PrometheusMetrics` is '
                'deprecated since 0.4.0, please use the '
                'new `group_by` argument.', DeprecationWarning
            )

            self.group_by = 'endpoint'

        elif group_by:
            self.group_by = group_by

        else:
            self.group_by = 'path'

        if excluded_paths:
            if PrometheusMetrics._is_string(excluded_paths):
                excluded_paths = [excluded_paths]

            self.excluded_paths = [
                re.compile(p) for p in excluded_paths
            ]
        else:
            self.excluded_paths = None

        if app is not None:
            self.init_app(app)

    @classmethod
    def for_app_factory(cls, **kwargs):
        """
        A convenience method to create a new instance that is
        suitable for Flask "app factory" configurations. Please
        see: http://flask.pocoo.org/docs/1.0/patterns/appfactories/

        Note, that you will need to call `init_app(...)` later
        with the Flask application as its parameter.

        This method takes the same keyword arguments as the
        default constructor.
        """

        return cls(app=None, **kwargs)

    def init_app(self, app):
        """
        This callback can be used to initialize an application for the
        use with this prometheus reporter setup.

        This is usually used with a Flask "app factory" configuration. Please
        see: http://flask.pocoo.org/docs/1.0/patterns/appfactories/

        Note, that you need to use `PrometheusMetrics.for_app_factory()`
        for this mode, otherwise it is called automatically.

        :param app: the Flask application
        """

        if self.path:
            self.register_endpoint(self.path, app)

        if self._export_defaults:
            self.export_defaults(
                self.buckets, self.group_by,
                self._defaults_prefix, app
            )

    def register_endpoint(self, path, app=None):
        """
        Register the metrics endpoint on the Flask application.

        :param path: the path of the endpoint
        :param app: the Flask application to register the endpoint on
            (by default it is the application registered with this class)
        """

        if is_running_from_reloader() and not os.environ.get('DEBUG_METRICS'):
            return

        if app is None:
            app = self.app or current_app

        @app.route(path)
        @self.do_not_track()
        def prometheus_metrics():
            # import these here so they don't clash with our own multiprocess module
            from prometheus_client import multiprocess, CollectorRegistry

            if 'prometheus_multiproc_dir' in os.environ:
                registry = CollectorRegistry()
            else:
                registry = self.registry

            if 'name[]' in request.args:
                registry = registry.restricted_registry(request.args.getlist('name[]'))

            if 'prometheus_multiproc_dir' in os.environ:
                multiprocess.MultiProcessCollector(registry)

            headers = {'Content-Type': CONTENT_TYPE_LATEST}
            return generate_latest(registry), 200, headers

    def start_http_server(self, port, host='0.0.0.0', endpoint='/metrics'):
        """
        Start an HTTP server for exposing the metrics.
        This will be an individual Flask application,
        not the one registered with this class.

        :param port: the HTTP port to expose the metrics endpoint on
        :param host: the HTTP host to listen on (default: `0.0.0.0`)
        :param endpoint: the URL path to expose the endpoint on
            (default: `/metrics`)
        """

        if is_running_from_reloader():
            return

        app = Flask('prometheus-flask-exporter-%d' % port)
        self.register_endpoint(endpoint, app)

        def run_app():
            app.run(host=host, port=port)

        thread = threading.Thread(target=run_app)
        thread.setDaemon(True)
        thread.start()

    def export_defaults(self, buckets=None, group_by='path',
                        prefix='flask', app=None, **kwargs):
        """
        Export the default metrics:
            - HTTP request latencies
            - HTTP request exceptions
            - Number of HTTP requests

        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param group_by: group default HTTP metrics by
            this request property, like `path`, `endpoint`, `rule`, etc.
            (defaults to `path`)
        :param prefix: prefix to start the default metrics names with
            or `NO_PREFIX` (to skip prefix)
        :param app: the Flask application
        """

        if app is None:
            app = self.app or current_app

        if not prefix:
            prefix = self._defaults_prefix or 'flask'

        # use the default buckets from prometheus_client if not given here
        buckets_as_kwargs = {}
        if buckets is not None:
            buckets_as_kwargs['buckets'] = buckets

        if kwargs.get('group_by_endpoint') is True:
            warnings.warn(
                'The `group_by_endpoint` argument of '
                '`PrometheusMetrics.export_defaults` is deprecated since 0.4.0, '
                'please use the new `group_by` argument.', DeprecationWarning
            )

            duration_group = 'endpoint'

        elif group_by:
            duration_group = group_by

        else:
            duration_group = 'path'

        if callable(duration_group):
            duration_group_name = duration_group.__name__

        else:
            duration_group_name = duration_group

        if prefix == NO_PREFIX:
            prefix = ""
        else:
            prefix = prefix + "_"

        try:
            self.info(
                '%sexporter_info' % prefix,
                'Information about the Prometheus Flask exporter',
                version=self.version
            )
        except ValueError:
            return  # looks like we have already exported the default metrics

        labels = self._get_combined_labels(None)

        request_duration_metric = Histogram(
            '%shttp_request_duration_seconds' % prefix,
            'Flask HTTP request duration in seconds',
            ('method', duration_group_name, 'status') + labels.keys(),
            registry=self.registry,
            **buckets_as_kwargs
        )

        counter_labels = ('method', 'status') + labels.keys()
        request_total_metric = Counter(
            '%shttp_request_total' % prefix,
            'Total number of HTTP requests',
            counter_labels,
            registry=self.registry
        )

        request_exceptions_metric = Counter(
            '%shttp_request_exceptions_total' % prefix,
            'Total number of HTTP requests which resulted in an exception',
            counter_labels,
            registry=self.registry
        )

        def before_request():
            request.prom_start_time = default_timer()

        def after_request(response):
            if hasattr(request, 'prom_do_not_track') or hasattr(request, 'prom_exclude_all'):
                return response

            if self.excluded_paths:
                if any(pattern.match(request.path) for pattern in self.excluded_paths):
                    return response

            if hasattr(request, 'prom_start_time'):
                total_time = max(default_timer() - request.prom_start_time, 0)

                if callable(duration_group):
                    group = duration_group(request)
                else:
                    group = getattr(request, duration_group)

                request_duration_labels = {
                    'method': request.method,
                    'status': _to_status_code(response.status_code),
                    duration_group_name: group
                }
                request_duration_labels.update(labels.values_for(response))

                request_duration_metric.labels(**request_duration_labels).observe(total_time)

            request_total_metric.labels(
                method=request.method, status=_to_status_code(response.status_code),
                **labels.values_for(response)
            ).inc()

            return response

        def teardown_request(exception=None):
            if not exception or hasattr(request, 'prom_do_not_track') or hasattr(request, 'prom_exclude_all'):
                return

            if self.excluded_paths:
                if any(pattern.match(request.path) for pattern in self.excluded_paths):
                    return

            # Check if the exception was raised using a response object and use
            # its status_code if present. This will only work for ``werkzeug.exceptions.HTTPException``
            # and subclasses thereof. Otherwise we assume it's a 500.
            try:
                response = exception.get_response()
                status_code = _to_status_code(response.status_code)
            except:
                status_code = 500
            finally:
                response = make_response('Exception: %s' % exception, status_code)

            if callable(duration_group):
                group = duration_group(request)
            else:
                group = getattr(request, duration_group)

            request_exceptions_metric.labels(
                method=request.method, status=status_code,
                **labels.values_for(response)
            ).inc()

            if hasattr(request, 'prom_start_time'):
                total_time = max(default_timer() - request.prom_start_time, 0)

                request_duration_labels = {
                    'method': request.method,
                    'status': status_code,
                    duration_group_name: group
                }
                request_duration_labels.update(labels.values_for(response))

                request_duration_metric.labels(**request_duration_labels).observe(total_time)

            request_total_metric.labels(
                method=request.method, status=500,
                **labels.values_for(response)
            ).inc()

            return

        app.before_request(before_request)
        app.after_request(after_request)
        app.teardown_request(teardown_request)

    def register_default(self, *metric_wrappers, **kwargs):
        """
        Registers metric wrappers to track all endpoints,
        similar to `export_defaults` but with user defined metrics.
        Call this function after all routes have been set up.

        Use the metric wrappers as arguments:
          - metrics.counter(..)
          - metrics.gauge(..)
          - metrics.summary(..)
          - metrics.histogram(..)

        :param metric_wrappers: one or more metric wrappers to register
            for all available endpoints
        :param app: the Flask application to register the default metric for
            (by default it is the application registered with this class)
        """

        app = kwargs.get('app')
        if app is None:
            app = self.app or current_app

        for endpoint, view_func in app.view_functions.items():
            for wrapper in metric_wrappers:
                view_func = wrapper(view_func)
                app.view_functions[endpoint] = view_func

    def histogram(self, name, description, labels=None, **kwargs):
        """
        Use a Histogram to track the execution time and invocation count
        of the method.

        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param kwargs: additional keyword arguments for creating the Histogram
        """

        return self._track(
            Histogram,
            lambda metric, time: metric.observe(time),
            kwargs, name, description, labels,
            registry=self.registry
        )

    def summary(self, name, description, labels=None, **kwargs):
        """
        Use a Summary to track the execution time and invocation count
        of the method.

        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param kwargs: additional keyword arguments for creating the Summary
        """

        return self._track(
            Summary,
            lambda metric, time: metric.observe(time),
            kwargs, name, description, labels,
            registry=self.registry
        )

    def gauge(self, name, description, labels=None, **kwargs):
        """
        Use a Gauge to track the number of invocations in progress
        for the method.

        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param kwargs: additional keyword arguments for creating the Gauge
        """

        return self._track(
            Gauge,
            lambda metric, time: metric.dec(),
            kwargs, name, description, labels,
            registry=self.registry,
            before=lambda metric: metric.inc(),
            revert_when_not_tracked=lambda metric: metric.dec()
        )

    def counter(self, name, description, labels=None, **kwargs):
        """
        Use a Counter to track the total number of invocations of the method.

        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param kwargs: additional keyword arguments for creating the Counter
        """

        return self._track(
            Counter,
            lambda metric, time: metric.inc(),
            kwargs, name, description, labels,
            registry=self.registry
        )

    def _track(self, metric_type, metric_call, metric_kwargs, name, description, labels,
               registry, before=None, revert_when_not_tracked=None):
        """
        Internal method decorator logic.

        :param metric_type: the type of the metric from the `prometheus_client` library
        :param metric_call: the invocation to execute as a callable with `(metric, time)`
        :param metric_kwargs: additional keyword arguments for creating the metric
        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param registry: the Prometheus Registry to use
        :param before: an optional callable to invoke before executing the
            request handler method accepting the single `metric` argument
        :param revert_when_not_tracked: an optional callable to invoke when
            a non-tracked endpoint is being handled to undo any actions already
            done on it, accepts a single `metric` argument
        """

        if labels is not None and not isinstance(labels, dict):
            raise TypeError('labels needs to be a dictionary of {labelname: callable}')

        labels = self._get_combined_labels(labels)

        parent_metric = metric_type(
            name, description, labelnames=labels.keys(), registry=registry,
            **metric_kwargs
        )

        def get_metric(response):
            if labels.has_keys():
                return parent_metric.labels(**labels.values_for(response))
            else:
                return parent_metric

        def decorator(f):
            @wraps(f)
            def func(*args, **kwargs):
                if before:
                    metric = get_metric(None)
                    before(metric)

                else:
                    metric = None

                exception = None

                start_time = default_timer()
                try:
                    try:
                        # execute the handler function
                        response = f(*args, **kwargs)
                    except Exception as ex:
                        # let Flask decide to wrap or reraise the Exception
                        response = current_app.handle_user_exception(ex)
                except Exception as ex:
                    # if it was re-raised, treat it as an InternalServerError
                    exception = ex
                    response = make_response('Exception: %s' % ex, 500)

                if hasattr(request, 'prom_exclude_all'):
                    if metric and revert_when_not_tracked:
                        # special handling for Gauge metrics
                        revert_when_not_tracked(metric)

                    return response

                total_time = max(default_timer() - start_time, 0)

                if not metric:
                    if not isinstance(response, Response) and request.endpoint:
                        view_func = current_app.view_functions[request.endpoint]

                        # There may be decorators 'above' us,
                        # but before the function is registered with Flask
                        while view_func and view_func != f:
                            try:
                                view_func = view_func.__wrapped__
                            except AttributeError:
                                break

                        if view_func == f:
                            # we are in a request handler method
                            response = self._response_converter(response)

                        elif hasattr(view_func, 'view_class') and isinstance(view_func.view_class, MethodViewType):
                            # we are in a method view (for Flask-RESTful for example)
                            response = self._response_converter(response)

                    metric = get_metric(response)

                metric_call(metric, time=total_time)

                if exception:
                    try:
                        # re-raise for the Flask error handler
                        raise exception
                    except Exception as ex:
                        return current_app.handle_user_exception(ex)

                else:
                    return response

            return func

        return decorator

    def _get_combined_labels(self, labels):
        """
        Combines the given labels with static and default labels
        and wraps them into an object that can efficiently return
        the keys and values of these combined labels.
        """

        labels = labels.copy() if labels else dict()

        if self._default_labels:
            labels.update(self._default_labels.copy())

        def argspec(func):
            if hasattr(inspect, 'getfullargspec'):
                return inspect.getfullargspec(func)
            else:
                return inspect.getargspec(func)

        def label_value(f):
            if not callable(f):
                return lambda x: f
            if argspec(f).args:
                return lambda x: f(x)
            else:
                return lambda x: f()

        class CombinedLabels(object):
            def __init__(self, _labels):
                self.labels = _labels.items()

            def keys(self):
                return tuple(map(lambda k: k[0], self.labels))

            def has_keys(self):
                return len(self.labels) > 0

            def values_for(self, response):
                label_generator = tuple(
                    (key, label_value(call))
                    for key, call in self.labels
                ) if labels else tuple()

                return {key: value(response) for key, value in label_generator}

        return CombinedLabels(labels)

    @staticmethod
    def do_not_track():
        """
        Decorator to skip the default metrics collection for the method.

        *Note*: explicit metrics decorators will still collect the data
        """

        def decorator(f):
            @wraps(f)
            def func(*args, **kwargs):
                request.prom_do_not_track = True
                return f(*args, **kwargs)

            return func

        return decorator

    @staticmethod
    def exclude_all_metrics():
        """
        Decorator to skip all metrics collection for the method.
        """

        def decorator(f):
            @wraps(f)
            def func(*args, **kwargs):
                request.prom_exclude_all = True
                return f(*args, **kwargs)

            return func

        return decorator

    def info(self, name, description, labelnames=None, labelvalues=None, **labels):
        """
        Report any information as a Prometheus metric.
        This will create a `Gauge` with the initial value of 1.

        The easiest way to use it is:

            metrics = PrometheusMetrics(app)
            metrics.info(
                'app_info', 'Application info',
                version='1.0', major=1, minor=0
            )

        If the order of the labels matters:

            metrics = PrometheusMetrics(app)
            metrics.info(
                'app_info', 'Application info',
                ('version', 'major', 'minor'),
                ('1.0', 1, 0)
            )

        :param name: the name of the metric
        :param description: the description of the metric
        :param labelnames: the names of the labels
        :param labelvalues: the values of the labels
        :param labels: the names and values of the labels
        :return: the newly created `Gauge` metric
        """

        if labels and labelnames:
            raise ValueError(
                'Cannot have labels defined as `dict` '
                'and collections of names and values'
            )

        if labelnames is None and labels:
            labelnames = labels.keys()

        elif labelnames and labelvalues:
            for idx, label_name in enumerate(labelnames):
                labels[label_name] = labelvalues[idx]

        gauge = Gauge(
            name, description, labelnames or tuple(),
            registry=self.registry
        )

        if labels:
            gauge = gauge.labels(**labels)

        gauge.set(1)

        return gauge

    @staticmethod
    def _is_string(value):
        try:
            return isinstance(value, basestring)  # python2
        except NameError:
            return isinstance(value, str)  # python3


class ConnexionPrometheusMetrics(PrometheusMetrics):
    """
    Specific extension for Connexion (https://connexion.readthedocs.io/)
    that makes sure responses are converted to Flask responses.
    """
    def __init__(self, app, default_mimetype='application/json', **kwargs):
        flask_app = app.app if app else None
        if 'response_converter' not in kwargs:
            kwargs['response_converter'] = self._create_response_converter(default_mimetype)

        super().__init__(flask_app, **kwargs)

    @staticmethod
    def content_type(content_type):
        """
        Force the content type of the response,
        which would be otherwise overwritten by the metrics conversion
        to application/json.

        :param content_type: the value to send in the
          Content-Type response header
        """

        def decorator(f):
            @wraps(f)
            def func(*args, **kwargs):
                request.prom_connexion_content_type = content_type
                return f(*args, **kwargs)
            return func
        return decorator

    @staticmethod
    def _create_response_converter(default_mimetype):
        from connexion.apis.flask_api import FlaskApi

        def _make_response(response):
            mimetype = default_mimetype
            if hasattr(request, 'prom_connexion_content_type'):
                mimetype = request.prom_connexion_content_type
            return FlaskApi.get_response(response, mimetype=mimetype)
        return _make_response


class RESTfulPrometheusMetrics(PrometheusMetrics):
    """
    Specific extension for Flask-RESTful (https://flask-restful.readthedocs.io/)
    that makes sure API responses are converted to Flask responses.
    """
    def __init__(self, app, api, **kwargs):
        """
        Initializes a new PrometheusMetrics instance that is appropriate
        for a Flask-RESTful application.

        :param app: the Flask application
        :param api: the Flask-RESTful API instance
        """

        if api and 'response_converter' not in kwargs:
            kwargs['response_converter'] = self._create_response_converter(api)
        super().__init__(app, **kwargs)

    @classmethod
    def for_app_factory(cls, api=None, **kwargs):
        return cls(app=None, api=api, **kwargs)

    def init_app(self, app, api=None):
        if api:
            self._response_converter = self._create_response_converter(api)
        return super().init_app(app)

    @staticmethod
    def _create_response_converter(api):
        def _make_response(response):
            if response is None:
                response = (None, 200)
            return api.make_response(*response)
        return _make_response


__version__ = '0.15.4'
