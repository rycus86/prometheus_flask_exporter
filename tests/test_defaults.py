from unittest_helper import BaseTestCase

from flask import make_response


class DefaultsTest(BaseTestCase):
    def test_simple(self):
        metrics = self.metrics()

        self.assertMetric(
            'prometheus_flask_exporter_info', '1.0',
            ('version', metrics.version)
        )

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('path', '/metrics'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '0.1'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '0.5'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '1.0'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '5.0'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '+Inf'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '3.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_response_object(self):
        metrics = self.metrics()

        @metrics.counter('success_invocation', 'Successful invocation')
        def success():
            return 200

        @self.app.route('/test')
        def test():
            return make_response('OK', success())

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

        self.assertMetric('success_invocation', '2.0')

    def test_skip(self):
        metrics = self.metrics()

        @self.app.route('/skip')
        @metrics.do_not_track()
        def test():
            return 'OK'

        self.client.get('/skip')
        self.client.get('/skip')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('path', '/skip'), ('status', 200)
        )

    def test_custom_path(self):
        self.metrics(path='/my-metrics')

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '1.0',
            ('method', 'GET'), ('status', 200),
            endpoint='/my-metrics'
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '1.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            endpoint='/my-metrics'
        )

    def test_no_default_export(self):
        self.metrics(export_defaults=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200),
            endpoint='/metrics'
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            endpoint='/metrics'
        )

    def test_non_automatic_endpoint_registration(self):
        metrics = self.metrics(path=None)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        no_metrics_response = self.client.get('/metrics')
        self.assertEqual(no_metrics_response.status_code, 404)

        metrics.register_endpoint('/manual/metrics')

        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200),
            endpoint='/manual/metrics'
        )

    def test_custom_buckets(self):
        self.metrics(buckets=(0.2, 2, 4))

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '0.2'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '2.0'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '4.0'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('le', '+Inf'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '0.1'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '0.3'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '1.2'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '5.0'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_invalid_labels(self):
        metrics = self.metrics()

        self.assertRaises(
            TypeError, metrics.counter,
            'invalid_counter', 'Counter with invalid labels',
            labels=('name', 'value')
        )

    def test_info(self):
        metrics = self.metrics()

        metrics.info('info', 'Info', x=1, y=2)

        self.assertMetric('info', '1.0', ('x', 1), ('y', 2))

        sample = metrics.info(
            'sample', 'Sample', ('key',), ('value',)
        )
        sample.set(5)

        self.assertMetric('sample', '5.0', ('key', 'value'))

        self.assertRaises(
            ValueError, metrics.info, 'invalid', 'Invalid',
            ('both', 'names'), ('and', 'values'), are='defined'
        )

        metrics.info('no_labels', 'Without labels')

        self.assertMetric('no_labels', '1.0')
