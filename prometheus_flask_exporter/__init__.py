import functools
from timeit import default_timer

from flask import request
from prometheus_client import Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from werkzeug.wsgi import DispatcherMiddleware


class PrometheusMetrics(object):
    def __init__(self, app, path='/metrics', export_defaults=True):
        self.app = app

        if path:
            self.register_endpoint(path)
        
        if export_defaults:
            self.export_defaults()

    def register_endpoint(self, path):
        @self.app.route(path)
        def prometheus_metrics():
            headers = {'Content-Type': CONTENT_TYPE_LATEST}
            return generate_latest(), 200, headers
    
    def export_defaults(self):
        summary = Summary(
            'http_request_duration_seconds', 
            'HTTP request duration in seconds',
            ('method', 'path', 'status')
        )

        def before_request():
            request.prom_start_time = default_timer()

        def after_request(response):
            total_time = max(default_timer() - request.prom_start_time, 0)
            summary.labels(
                request.method, request.path, response.status_code
            ).observe(total_time)

            return response

        self.app.before_request(before_request)
        self.app.after_request(after_request)

