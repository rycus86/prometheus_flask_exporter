import inspect
import functools
from timeit import default_timer

from flask import request
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

        @app.route('/')
        def main():
            pass  # requests tracked by default

        @app.route('/skip')
        @metrics.do_not_track()
        def skip():
            pass  # default metrics are not collected

        @app.route('/<item_type>')
        @metrics.do_not_track()
        @counter('invocation_by_type', 'Number of invocations by type',
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

    def __init__(self, app, path='/metrics', export_defaults=True,
                 buckets=(0.1, 0.3, 1.2, 5), registry=DEFAULT_REGISTRY):
        """
        Create a new Prometheus metrics export configuration.

        :param app: the Flask application
        :param path: the metrics path (defaults to `/metrics`)
        :param export_defaults: expose all HTTP request latencies
            and number of HTTP requests
        :param buckets: the time buckets for request latencies
        :param registry: the Prometheus Registry to use
        """

        self.app = app
        self.registry = registry

        if path:
            self.register_endpoint(path)

        if export_defaults:
            self.export_defaults(buckets)

    def register_endpoint(self, path):
        """
        Register the metrics endpoint on the Flask application.

        :param path: the path of the endpoint
        """

        @self.app.route(path)
        @self.do_not_track()
        def prometheus_metrics():
            headers = {'Content-Type': CONTENT_TYPE_LATEST}
            return generate_latest(self.registry), 200, headers

    def export_defaults(self, buckets=(0.1, 0.3, 1.2, 5)):
        """
        Export the default metrics:
            - HTTP request latencies
            - Number of HTTP requests

        :param buckets: the time buckets for request latencies
        """

        histogram = Histogram(
            'flask_http_request_duration_seconds',
            'Flask HTTP request duration in seconds',
            ('method', 'path', 'status'),
            buckets=buckets,
            registry=self.registry
        )

        counter = Counter(
            'flask_http_request_total',
            'Total number of HTTP requests',
            ('method', 'status'),
            registry=self.registry
        )

        def before_request():
            request.prom_start_time = default_timer()

        def after_request(response):
            if hasattr(request, 'prom_do_not_track'):
                return response

            total_time = max(default_timer() - request.prom_start_time, 0)
            histogram.labels(
                request.method, request.path, response.status_code
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
        :param labels: a dictionary of `{labelname: callable}` for labels
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
        :param labels: a dictionary of `{labelname: callable}` for labels
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
        :param labels: a dictionary of `{labelname: callable}` for labels
        :param kwargs: additional keyword arguments for creating the Gauge
        """

        return self._track(
            Gauge,
            lambda metric, time: metric.dec(),
            kwargs, name, description, labels,
            before=lambda metric: metric.inc(),
            registry=self.registry
        )

    def counter(self, name, description, labels=None, **kwargs):
        """
        Use a Counter to track the total number of invocations of the method.

        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable}` for labels
        :param kwargs: additional keyword arguments for creating the Counter
        """

        return self._track(
            Counter,
            lambda metric, time: metric.inc(),
            kwargs, name, description, labels,
            registry=self.registry
        )

    @staticmethod
    def _track(metric_type, metric_call, metric_kwargs, name, description, labels, before=None):
        """
        Internal method decorator logic.

        :param metric_type: the type of the metric from the `prometheus_client` library
        :param metric_call: the invocation to execute as a callable with `(metric, time)`
        :param metric_kwargs: additional keyword arguments for creating the metric
        :param name: the name of the metric
        :param description: the description of the metric
        :param labels: a dictionary of `{labelname: callable}` for labels
        :param before: an optional callable to invoke before executing the
            request handler method accepting the single `metric` argument
        """

        if labels is not None and not isinstance(labels, dict):
            raise TypeError('labels needs to be a dictionary of {labelname: callable}')

        def wrap_call(f):
            if inspect.getargspec(f).args:
                return lambda x: f(x)
            else:
                return lambda x: f()

        def get_metric(response):
            if label_names:
                return parent_metric.labels(
                    **{key: call(response) for key, call in label_generator}
                )
            else:
                return parent_metric

        label_names = labels.keys() if labels else tuple()
        parent_metric = metric_type(name, description, labelnames=label_names, **metric_kwargs)

        label_generator = tuple(
            (key, wrap_call(call))
            for key, call in labels.items()
        ) if labels else tuple()

        def decorator(f):
            @functools.wraps(f)
            def func(*args, **kwargs):
                if before:
                    metric = get_metric(None)
                    before(metric)

                else:
                    metric = None

                start_time = default_timer()
                response = f(*args, **kwargs)
                total_time = max(default_timer() - start_time, 0)

                if not metric:
                    metric = get_metric(response)

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
