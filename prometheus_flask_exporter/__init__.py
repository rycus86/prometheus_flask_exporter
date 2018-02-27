import inspect
import functools
import threading
from timeit import default_timer

from flask import request, make_response
from flask import Flask, Response
from werkzeug.exceptions import HTTPException
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY as DEFAULT_REGISTRY


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
                 export_defaults=True, group_by_endpoint=False,
                 buckets=None, registry=DEFAULT_REGISTRY):
        """
        Create a new Prometheus metrics export configuration.

        :param app: the Flask application
        :param path: the metrics path (defaults to `/metrics`)
        :param export_defaults: expose all HTTP request latencies
            and number of HTTP requests
        :param group_by_endpoint: group default HTTP metrics
            by the endpoints' function name instead of the URI path
        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param registry: the Prometheus Registry to use
        """

        self.app = app
        self.registry = registry
        self.version = __version__

        if path:
            self.register_endpoint(path)

        if export_defaults:
            self.export_defaults(buckets, group_by_endpoint)

    def register_endpoint(self, path, app=None):
        """
        Register the metrics endpoint on the Flask application.

        :param path: the path of the endpoint
        :param app: the Flask application to register the endpoint on
            (by default it is the application registered with this class)
        """

        if app is None:
            app = self.app

        @app.route(path)
        @self.do_not_track()
        def prometheus_metrics():
            registry = self.registry
            if 'name[]' in request.args:
                registry = registry.restricted_registry(request.args.getlist('name[]'))

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

        app = Flask('prometheus-flask-exporter-%d' % port)
        self.register_endpoint(endpoint, app)

        def run_app():
            app.run(host=host, port=port)

        thread = threading.Thread(target=run_app)
        thread.setDaemon(True)
        thread.start()

    def export_defaults(self, buckets=None, group_by_endpoint=False):
        """
        Export the default metrics:
            - HTTP request latencies
            - Number of HTTP requests

        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param group_by_endpoint: group default HTTP metrics
            by the endpoints' function name instead of the URI path
        """

        # use the default buckets from prometheus_client if not given here
        buckets_as_kwargs = {}
        if buckets is not None:
            buckets_as_kwargs['buckets'] = buckets

        duration_group = 'endpoint' if group_by_endpoint else 'path'

        histogram = Histogram(
            'flask_http_request_duration_seconds',
            'Flask HTTP request duration in seconds',
            ('method', duration_group, 'status'),
            registry=self.registry,
            **buckets_as_kwargs
        )

        counter = Counter(
            'flask_http_request_total',
            'Total number of HTTP requests',
            ('method', 'status'),
            registry=self.registry
        )

        self.info(
            'flask_exporter_info',
            'Information about the Prometheus Flask exporter',
            version=self.version
        )

        def before_request():
            request.prom_start_time = default_timer()

        def after_request(response):
            if hasattr(request, 'prom_do_not_track'):
                return response

            total_time = max(default_timer() - request.prom_start_time, 0)
            histogram.labels(
                request.method,
                getattr(request, duration_group),
                response.status_code
            ).observe(total_time)

            counter.labels(request.method, response.status_code).inc()

            return response

        self.app.before_request(before_request)
        self.app.after_request(after_request)

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
            before=lambda metric: metric.inc()
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

    @staticmethod
    def _track(metric_type, metric_call, metric_kwargs, name, description, labels,
               registry, before=None):
        """
        Internal method decorator logic.

        :param metric_type: the type of the metric from the `prometheus_client` library
        :param metric_call: the invocation to execute as a callable with `(metric, time)`
        :param metric_kwargs: additional keyword arguments for creating the metric
        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable_or_value}` for labels
        :param before: an optional callable to invoke before executing the
            request handler method accepting the single `metric` argument
        :param registry: the Prometheus Registry to use
        """

        if labels is not None and not isinstance(labels, dict):
            raise TypeError('labels needs to be a dictionary of {labelname: callable}')

        label_names = labels.keys() if labels else tuple()
        parent_metric = metric_type(
            name, description, labelnames=label_names, registry=registry,
            **metric_kwargs
        )

        def label_value(f):
            if not callable(f):
                return lambda x: f
            if inspect.getargspec(f).args:
                return lambda x: f(x)
            else:
                return lambda x: f()

        label_generator = tuple(
            (key, label_value(call))
            for key, call in labels.items()
        ) if labels else tuple()

        def get_metric(response):
            if label_names:
                return parent_metric.labels(
                    **{key: call(response) for key, call in label_generator}
                )
            else:
                return parent_metric

        def decorator(f):
            @functools.wraps(f)
            def func(*args, **kwargs):
                if before:
                    metric = get_metric(None)
                    before(metric)

                else:
                    metric = None

                start_time = default_timer()
                try:
                    response = f(*args, **kwargs)
                except HTTPException as ex:
                    response = ex
                except Exception as ex:
                    response = make_response('Exception: %s' % ex, 500)

                total_time = max(default_timer() - start_time, 0)

                if not metric:
                    response_for_metric = response

                    if not isinstance(response, Response):
                        if request.endpoint == f.__name__:
                            # we are in a request handler method
                            response_for_metric = make_response(response)

                    metric = get_metric(response_for_metric)

                metric_call(metric, time=total_time)
                return response

            return func

        return decorator

    @staticmethod
    def do_not_track():
        """
        Decorator to skip the default metrics collection for the method.

        *Note*: explicit metrics decorators will still collect the data
        """

        def decorator(f):
            @functools.wraps(f)
            def func(*args, **kwargs):
                request.prom_do_not_track = True
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
            name, description, labelnames,
            registry=self.registry
        )

        if labels:
            gauge = gauge.labels(**labels)

        gauge.set(1)

        return gauge


__version__ = '0.2.0'
