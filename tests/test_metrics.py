from unittest_helper import BaseTestCase

from flask import request


class MetricsTest(BaseTestCase):
    def test_histogram(self):
        metrics = self.metrics()

        @self.app.route('/test/1')
        @metrics.histogram('hist_1', 'Histogram 1')
        def test1():
            return 'OK'

        self.client.get('/test/1')

        self.assertMetric('hist_1_count', '1.0')
        self.assertMetric('hist_1_bucket', '1.0', ('le', '2.5'))

        @self.app.route('/test/2')
        @metrics.histogram('hist_2', 'Histogram 2', labels={
            'uri': lambda: request.path, 
            'code': lambda r: r.status_code
        })
        def test2():
            return 'OK'

        self.client.get('/test/2')

        self.assertMetric(
            'hist_2_count', '1.0',
            ('uri', '/test/2'), ('code', 200)
        )

