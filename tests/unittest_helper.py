import re
import sys
import unittest

from flask import Flask
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics


class BaseTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

    def metrics(self, **kwargs):
        registry = kwargs.pop('registry', CollectorRegistry(auto_describe=True))
        return PrometheusMetrics(self.app, registry=registry, **kwargs)

    def assertMetric(self, name, value, *labels, **kwargs):
        if labels:
            pattern = r'(?ms).*%s\{(%s)\} %s.*' % (
                name, ','.join(
                    '(?:%s)="(?:%s)"' % (
                        '|'.join(str(item) for item, _ in labels),
                        '|'.join(str(item).replace('+', r'\+') for _, item in labels)
                    ) for _ in labels
                ), value
            )
        else:
            pattern = '(?ms).*%s %s.*' % (name, value)

        response = self.client.get(kwargs.get('endpoint', '/metrics'))
        self.assertEqual(response.status_code, 200)
        self.assertRegex(str(response.data), pattern)

        if not labels:
            return

        match = re.sub(pattern, r'\1', str(response.data))

        for item in labels:
            self.assertIn(('%s="%s"' % item), match)

    def assertAbsent(self, name, *labels, **kwargs):
        if labels:
            pattern = r'(?ms).*%s\{(%s)\} .*' % (
                name, ','.join(
                    '(?:%s)="(?:%s)"' % (
                        '|'.join(str(item) for item, _ in labels),
                        '|'.join(str(item).replace('+', r'\+') for _, item in labels)
                    ) for _ in labels
                )
            )
        else:
            pattern = '.*%s [0-9.]+.*' % name

        response = self.client.get(kwargs.get('endpoint', '/metrics'))
        self.assertEqual(response.status_code, 200)
        self.assertNotRegex(str(response.data), pattern)
