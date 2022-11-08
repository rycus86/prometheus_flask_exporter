from unittest_helper import BaseTestCase

from flask import request


class MetricsTest(BaseTestCase):
    def test_histogram(self):
        metrics = self.metrics()

        @self.app.route('/test/1')
        @metrics.histogram('hist_1', 'Histogram 1')
        def test1():
            return 'OK'

        @self.app.route('/test/2')
        @metrics.histogram('hist_2', 'Histogram 2', labels={
            'uri': lambda: request.path,
            'code': lambda r: r.status_code
        })
        def test2():
            return 'OK'

        @self.app.route('/test/<int:x>/<int:y>')
        @metrics.histogram('hist_3', 'Histogram 3', labels={
            'x_value': lambda: request.view_args['x'],
            'y_value': lambda: request.view_args['y']
        }, buckets=(0.7, 2.9))
        def test3(x, y):
            return 'OK: %d/%d' % (x, y)

        self.assertMetric('hist_1_count', '0.0')

        self.client.get('/test/1')

        self.assertMetric('hist_1_count', '1.0')
        self.assertMetric('hist_1_bucket', '1.0', ('le', '2.5'))

        self.client.get('/test/2')

        self.assertMetric(
            'hist_2_count', '1.0',
            ('uri', '/test/2'), ('code', 200)
        )
        self.assertMetric(
            'hist_2_bucket', '1.0',
            ('le', '1.0'), ('uri', '/test/2'), ('code', 200)
        )

        self.client.get('/test/3/4')

        self.assertMetric(
            'hist_3_count', '1.0',
            ('x_value', '3'), ('y_value', '4')
        )
        self.assertMetric(
            'hist_3_bucket', '1.0',
            ('le', '0.7'), ('x_value', '3'), ('y_value', '4')
        )

    def test_summary(self):
        metrics = self.metrics()

        @self.app.route('/test/1')
        @metrics.summary('sum_1', 'Summary 1')
        def test1():
            return 'OK'

        @self.app.route('/test/2')
        @metrics.summary('sum_2', 'Summary 2', labels={
            'uri': lambda: request.path,
            'code': lambda r: r.status_code,
            'variant': 2
        })
        def test2():
            return 'OK'

        self.assertMetric('sum_1_count', '0.0')

        self.client.get('/test/1')

        self.assertMetric('sum_1_count', '1.0')

        self.client.get('/test/2')

        self.assertMetric(
            'sum_2_count', '1.0',
            ('uri', '/test/2'), ('code', 200), ('variant', 2)
        )

    def test_gauge(self):
        metrics = self.metrics()

        @self.app.route('/test/1')
        @metrics.gauge('gauge_1', 'Gauge 1')
        def test1():
            self.assertMetric('gauge_1', '1.0')

            return 'OK'

        @self.app.route('/test/<int:a>')
        @metrics.gauge('gauge_2', 'Gauge 2', labels={
            'uri': lambda: request.path,
            'a_value': lambda: request.view_args['a']
        })
        def test2(a):
            self.assertMetric(
                'gauge_2', '1.0',
                ('uri', '/test/2'), ('a_value', 2)
            )

            return 'OK: %d' % a

        self.assertMetric('gauge_1', '0.0')

        self.client.get('/test/1')

        self.assertMetric('gauge_1', '0.0')

        self.client.get('/test/2')

        self.assertMetric(
            'gauge_2', '0.0',
            ('uri', '/test/2'), ('a_value', 2)
        )

    def test_counter(self):
        metrics = self.metrics()

        @self.app.route('/test/1')
        @metrics.counter('cnt_1', 'Counter 1')
        def test1():
            return 'OK'

        @self.app.route('/test/2')
        @metrics.counter('cnt_2', 'Counter 2', labels={
            'uri': lambda: request.path,
            'code': lambda r: r.status_code
        })
        def test2():
            return 'OK'

        self.assertMetric('cnt_1_total', '0.0')
        self.client.get('/test/1')
        self.assertMetric('cnt_1_total', '1.0')
        self.client.get('/test/1')
        self.assertMetric('cnt_1_total', '2.0')
        self.client.get('/test/1')
        self.assertMetric('cnt_1_total', '3.0')

        self.client.get('/test/2')

        self.assertMetric(
            'cnt_2_total', '1.0',
            ('uri', '/test/2'), ('code', 200)
        )

    def test_default_format(self):
        self.metrics()

        @self.app.route('/example')
        def test():
            return 'OK'

        for _ in range(5):
            self.client.get('/example')

        from prometheus_client.exposition import CONTENT_TYPE_LATEST

        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, CONTENT_TYPE_LATEST)

        self.assertNotIn('# EOF', str(response.data))
        self.assertRegex(
            str(response.data),
            'flask_http_request_duration_seconds_count\\{[^}]+\\} 5.0')

    def test_openmetrics_format(self):
        self.metrics()

        @self.app.route('/example')
        def test():
            return 'OK'

        for _ in range(5):
            self.client.get('/example')

        from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

        response = self.client.get('/metrics', headers={'Accept': 'application/openmetrics-text'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, CONTENT_TYPE_LATEST)

        self.assertIn('# EOF', str(response.data))
        self.assertRegex(
            str(response.data),
            'flask_http_request_duration_seconds_count\\{[^}]+\\} 5.0')
