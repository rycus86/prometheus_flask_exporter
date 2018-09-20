import sys
import unittest

from flask import Flask
from unittest_helper import BaseTestCase
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import CollectorRegistry
from flask import request, abort

class AppFactoryTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(AppFactoryTest, self).__init__(*args, **kwargs)
        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

        registry = CollectorRegistry(auto_describe=True)
        self.metrics = PrometheusMetrics(registry=registry)
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
