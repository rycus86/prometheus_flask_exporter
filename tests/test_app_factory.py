from unittest_helper import BaseTestCase
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import CollectorRegistry
from flask import request, abort

class AppFactoryTest(BaseTestCase):

    def metrics_init(self, **kwargs):
        registry = kwargs.pop('registry', CollectorRegistry(auto_describe=True))
        metrics = PrometheusMetrics(registry=registry, **kwargs)
        metrics.init_app(self.app)

        return metrics

    def test_restricted(self):
        self.metrics_init()

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/metrics?name[]=flask_exporter_info')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/metrics'
                                   '?name[]=flask_http_request_duration_seconds_bucket'
                                   '&name[]=flask_http_request_duration_seconds_count'
                                   '&name[]=flask_http_request_duration_seconds_sum')
        self.assertEqual(response.status_code, 200)
