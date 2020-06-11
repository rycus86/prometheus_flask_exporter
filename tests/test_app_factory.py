import sys
import unittest

from flask import Flask
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics


class AppFactoryTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

        registry = CollectorRegistry(auto_describe=True)
        self.metrics = PrometheusMetrics.for_app_factory(registry=registry)
        self.metrics.init_app(self.app)

    def test_restricted(self):
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

        self.assertIn('flask_http_request_duration_seconds_bucket{le="0.1",method="GET",path="/test",status="200"} 1.0',
                      str(response.data))
        self.assertIn('flask_http_request_duration_seconds_count{method="GET",path="/test",status="200"} 1.0',
                      str(response.data))
