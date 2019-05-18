import sys
import unittest

from flask import Flask, Blueprint
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics


class BlueprintTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

        registry = CollectorRegistry(auto_describe=True)
        self.metrics = PrometheusMetrics(app=None, registry=registry)

    def test_blueprint(self):
        blueprint = Blueprint('test-blueprint', __name__)

        @blueprint.route('/test')
        @self.metrics.summary('requests_by_status', 'Request latencies by status',
                              labels={'status': lambda r: r.status_code})
        def test():
            return 'OK'

        self.app.register_blueprint(blueprint)
        self.metrics.init_app(self.app)

        self.client.get('/test')

        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertIn('requests_by_status_count{status="200"} 1.0', str(response.data))
        self.assertRegex(str(response.data), 'requests_by_status_sum{status="200"} [0-9.]+')
