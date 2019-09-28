import os
from abc import ABCMeta, abstractmethod

from prometheus_client import CollectorRegistry
from prometheus_client import start_http_server as pc_start_http_server
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.multiprocess import mark_process_dead as pc_mark_process_dead

from . import PrometheusMetrics


def _check_multiproc_env_var():
    """
    Checks that the `prometheus_multiproc_dir` environment variable is set,
    which is required for the multiprocess collector to work properly.

    :raises ValueError: if the environment variable is not set
        or if it does not point to a directory
    """

    prometheus_dir = os.getenv('prometheus_multiproc_dir') or os.getenv('PROMETHEUS_MULTIPROC_DIR')
    if prometheus_dir and os.path.isdir(prometheus_dir):
        return

    raise ValueError('env prometheus_multiproc_dir/PROMETHEUS_MULTIPROC_DIR '
                     'is not set or not a directory')


class MultiprocessPrometheusMetrics(PrometheusMetrics):
    """
    An extension of the `PrometheusMetrics` class that provides
    convenience functions for multiprocess applications.

    There are ready to use classes for uWSGI and Gunicorn.
    For everything else, extend this class and override
    the `should_start_http_server` to only return `True`
    from one process only - typically the main one.

    Note: you will need to explicitly call the `start_http_server` function.
    """

    __metaclass__ = ABCMeta

    def __init__(self, app=None, export_defaults=True,
                 defaults_prefix='flask', group_by='path',
                 buckets=None, static_labels=None, registry=None):
        """
        Create a new multiprocess-aware Prometheus metrics export configuration.

        :param app: the Flask application (can be `None`)
        :param export_defaults: expose all HTTP request latencies
            and number of HTTP requests
        :param defaults_prefix: string to prefix the default exported
            metrics name with (when either `export_defaults=True` or
            `export_defaults(..)` is called)
        :param group_by: group default HTTP metrics by
            this request property, like `path`, `endpoint`, `url_rule`, etc.
            (defaults to `path`)
        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param static_labels: static labels to attach to each of the
            metrics exposed by this metrics instance
        :param registry: the Prometheus Registry to use (can be `None` and it
            will be registered with `prometheus_client.multiprocess.MultiProcessCollector`)
        """

        _check_multiproc_env_var()

        registry = registry or CollectorRegistry()
        MultiProcessCollector(registry)

        super(MultiprocessPrometheusMetrics, self).__init__(
            app=app, path=None, export_defaults=export_defaults,
            defaults_prefix=defaults_prefix, group_by=group_by,
            buckets=buckets, static_labels=static_labels,
            registry=registry
        )

    def start_http_server(self, port, host='0.0.0.0', endpoint=None):
        """
        Start an HTTP server for exposing the metrics, if the
        `should_start_http_server` function says we should, otherwise just return.
        Uses the implementation from `prometheus_client` rather than a Flask app.

        :param port: the HTTP port to expose the metrics endpoint on
        :param host: the HTTP host to listen on (default: `0.0.0.0`)
        :param endpoint: **ignored**, the HTTP server will respond on any path
        """

        if self.should_start_http_server():
            pc_start_http_server(port, host, registry=self.registry)

    @abstractmethod
    def should_start_http_server(self):
        """
        Whether or not to start the HTTP server.
        Only return `True` from one process only, typically the main one.

        Note: you still need to explicitly call the `start_http_server` function.

        :return: `True` if the server should start, `False` otherwise
        """

        pass


class UWsgiPrometheusMetrics(MultiprocessPrometheusMetrics):
    """
    A multiprocess `PrometheusMetrics` extension targeting uWSGI deployments.
    This will only start the HTTP server for metrics on the main process,
    indicated by `uwsgi.masterpid()`.
    """

    def should_start_http_server(self):
        import uwsgi
        return os.getpid() == uwsgi.masterpid()


class GunicornPrometheusMetrics(MultiprocessPrometheusMetrics):
    """
    A multiprocess `PrometheusMetrics` extension targeting Gunicorn deployments.
    This variant is expected to serve the metrics endpoint on an individual HTTP server.
    See `GunicornInternalPrometheusMetrics` for one that serves the metrics endpoint
    on the same server as the other endpoints.

    It should have Gunicorn configuration to start the HTTP server like this:

        from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

        def when_ready(server):
            GunicornPrometheusMetrics.start_http_server_when_ready(metrics_port)

        def child_exit(server, worker):
            GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)

    Alternatively, you can use the instance functions as well.
    """

    def should_start_http_server(self):
        return True

    @classmethod
    def start_http_server_when_ready(cls, port, host='0.0.0.0'):
        """
        Start the HTTP server from the Gunicorn config module.
        Doesn't necessarily need an instance, a class is fine.

        Example:

            def when_ready(server):
                GunicornPrometheusMetrics.start_http_server_when_ready(metrics_port)

        :param port: the HTTP port to expose the metrics endpoint on
        :param host: the HTTP host to listen on (default: `0.0.0.0`)
        """

        _check_multiproc_env_var()

        GunicornPrometheusMetrics().start_http_server(port, host)

    @classmethod
    def mark_process_dead_on_child_exit(cls, pid):
        """
        Mark a child worker as exited from the Gunicorn config module.

        Example:

            def child_exit(server, worker):
                GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)

        :param pid: the worker pid that has exited
        """

        pc_mark_process_dead(pid)


class GunicornInternalPrometheusMetrics(GunicornPrometheusMetrics):
    """
    A multiprocess `PrometheusMetrics` extension targeting Gunicorn deployments.
    This variant is expected to expose the metrics endpoint on the same server
    as the production endpoints are served too.
    See also the `GunicornPrometheusMetrics` class that will start a
    new HTTP server for the metrics endpoint.

    It should have Gunicorn configuration to start the HTTP server like this:

        from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

        def child_exit(server, worker):
            GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)

    Alternatively, you can use the instance functions as well.
    """

    def __init__(self, app=None, path='/metrics', export_defaults=True,
                 defaults_prefix='flask', group_by='path',
                 buckets=None, static_labels=None, registry=None):
        """
        Create a new multiprocess-aware Prometheus metrics export configuration.

        :param app: the Flask application (can be `None`)
        :param path: the metrics path (defaults to `/metrics`)
        :param export_defaults: expose all HTTP request latencies
            and number of HTTP requests
        :param defaults_prefix: string to prefix the default exported
            metrics name with (when either `export_defaults=True` or
            `export_defaults(..)` is called)
        :param group_by: group default HTTP metrics by
            this request property, like `path`, `endpoint`, `url_rule`, etc.
            (defaults to `path`)
        :param buckets: the time buckets for request latencies
            (will use the default when `None`)
        :param static_labels: static labels to attach to each of the
            metrics exposed by this metrics instance
        :param registry: the Prometheus Registry to use (can be `None` and it
            will be registered with `prometheus_client.multiprocess.MultiProcessCollector`)
        """

        super(GunicornInternalPrometheusMetrics, self).__init__(
            app=app, export_defaults=export_defaults,
            defaults_prefix=defaults_prefix, group_by=group_by,
            buckets=buckets, static_labels=static_labels,
            registry=registry
        )

        if app:
            self.register_endpoint(path)
        else:
            self.path = path

    def should_start_http_server(self):
        return False

    @classmethod
    def start_http_server_when_ready(cls, port, host='0.0.0.0'):
        import warnings
        warnings.warn(
            'The `GunicornInternalPrometheusMetrics` class is expected to expose the metrics endpoint '
            'on the same Flask application, so the `start_http_server_when_ready` should not be called. '
            'Maybe you are looking for the `GunicornPrometheusMetrics` class?',
            UserWarning
        )
