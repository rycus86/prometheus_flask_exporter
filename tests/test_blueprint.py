import sys
import unittest

from flask import Flask, Blueprint, request
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics, RESTfulPrometheusMetrics


class BlueprintTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

        registry = CollectorRegistry(auto_describe=True)
        self.metrics = PrometheusMetrics.for_app_factory(registry=registry)

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

    def test_restful_with_blueprints(self):
        try:
            from flask_restful import Resource, Api
        except ImportError:
            self.skipTest('Flask-RESTful is not available')
            return

        class SampleResource(Resource):
            status = 200

            @self.metrics.summary('requests_by_status', 'Request latencies by status',
                                  labels={'status': lambda r: r.status_code})
            def get(self):
                if 'fail' in request.args:
                    return 'Not OK', 400
                else:
                    return 'OK'

        blueprint = Blueprint('v1', __name__, url_prefix='/v1')
        api = Api(blueprint)

        api.add_resource(SampleResource, '/sample', endpoint='api_sample')

        self.app.register_blueprint(blueprint)
        self.metrics.init_app(self.app)

        self.client.get('/v1/sample')
        self.client.get('/v1/sample')
        self.client.get('/v1/sample?fail=1')

        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)

        self.assertIn('requests_by_status_count{status="200"} 2.0', str(response.data))
        self.assertRegex(str(response.data), 'requests_by_status_sum{status="200"} [0-9.]+')

        self.assertIn('requests_by_status_count{status="400"} 1.0', str(response.data))
        self.assertRegex(str(response.data), 'requests_by_status_sum{status="400"} [0-9.]+')

    def test_restful_return_none(self):
        try:
            from flask_restful import Resource, Api
        except ImportError:
            self.skipTest('Flask-RESTful is not available')
            return

        api = Api(self.app)
        self.metrics = RESTfulPrometheusMetrics(self.app, api=api)

        class SampleResource(Resource):
            status = 200

            @self.metrics.summary('requests_by_status', 'Request latencies by status',
                                  labels={'status': lambda r: r.status_code})
            def get(self):
                if 'fail' in request.args:
                    return None, 400, {'X-Error': 'Test error'}
                else:
                    return None

        api.add_resource(SampleResource, '/v1/sample', endpoint='api_sample')

        self.client.get('/v1/sample')
        self.client.get('/v1/sample')
        self.client.get('/v1/sample?fail=1')

        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)

        self.assertIn('requests_by_status_count{status="200"} 2.0', str(response.data))
        self.assertRegex(str(response.data), 'requests_by_status_sum{status="200"} [0-9.]+')

        self.assertIn('requests_by_status_count{status="400"} 1.0', str(response.data))
        self.assertRegex(str(response.data), 'requests_by_status_sum{status="400"} [0-9.]+')
