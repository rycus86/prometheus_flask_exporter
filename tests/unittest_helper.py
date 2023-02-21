import re
import sys
import unittest

import prometheus_client
from flask import Flask

from prometheus_flask_exporter import PrometheusMetrics


class BaseTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sys.version_info.major < 3:
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.client = self.app.test_client()

        # reset the underlying Prometheus registry
        prometheus_client.REGISTRY = prometheus_client.CollectorRegistry(auto_describe=True)

    def metrics(self, **kwargs):
        return PrometheusMetrics(self.app, registry=kwargs.pop('registry', None), **kwargs)

    def assertMetric(self, name, value, *labels, **kwargs):
        if labels:
            pattern = r'(?ms).*%s\{(%s)\} %s.*' % (
                name, ','.join(
                    '(?:%s)="(?:%s)"' % (
                        '|'.join(str(item) for item, _ in labels),
                        '|'.join(
                            str(item).replace('+', r'\+').replace('?', r'\?')
                            for _, item in labels
                        )
                    ) for _ in labels
                ), value
            )
        else:
            pattern = '(?ms).*%s %s.*' % (name, value)

        response = self.client.get(kwargs.get('endpoint', '/metrics'))
        self.assertEqual(response.status_code, 200)
        self.assertRegex(
            str(response.data), pattern,
            msg='Failing metric: %s%s, Regexp didn\'t match' % (name, dict(labels))
        )

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

    def assumeMinimumFlaskVersion(self, version):
        from flask import __version__ as flask_version

        desired_version = list(map(int, version.split('.')))
        actual_version = list(map(int, flask_version.split('.')))

        if actual_version < desired_version:
            self.skipTest(reason='Flask version %s is before the desired version %s' % (flask_version, version))

    def assumeBeforeFlaskVersion(self, version):
        from flask import __version__ as flask_version

        desired_version = list(map(int, version.split('.')))
        actual_version = list(map(int, flask_version.split('.')))

        if actual_version >= desired_version:
            self.skipTest(reason='Flask version %s is not before the desired version %s' % (flask_version, version))
