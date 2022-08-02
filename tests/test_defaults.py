from unittest_helper import BaseTestCase

from prometheus_flask_exporter import NO_PREFIX
from flask import request, make_response
from werkzeug.exceptions import Conflict


class DefaultsTest(BaseTestCase):
    def test_simple(self):
        metrics = self.metrics()

        @self.app.route('/test')
        def test():
            return 'OK'

        self.assertMetric(
            'flask_exporter_info', '1.0',
            ('version', metrics.version)
        )

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
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/skip/defaults'), ('status', 200)
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

        self.assertMetric('success_invocation_total', '2.0')

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

    def test_exception_counter_metric(self):
        self.metrics()

        @self.app.route('/error')
        def test_error():
            raise AttributeError

        @self.app.route('/abort')
        def test_abort():
            return Conflict()

        try:
            self.client.get('/error')
        except AttributeError:
            pass

        self.assertMetric(
            'flask_http_request_exceptions_total', '1.0',
            ('method', 'GET'), ('status', 500)
        )

        for _ in range(3):
            try:
                self.client.get('/error')
            except AttributeError:
                pass

        self.assertMetric(
            'flask_http_request_exceptions_total', '4.0',
            ('method', 'GET'), ('status', 500)
        )

        for _ in range(5):
            self.client.get('/abort')

        self.assertMetric(
            'flask_http_request_exceptions_total', '4.0',
            ('method', 'GET'), ('status', 500)
        )
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('status', 409)
        )
        self.assertMetric(
            'flask_http_request_total', '5.0',
            ('method', 'GET'), ('status', 409)
        )

    def test_do_not_track_only_excludes_defaults(self):
        metrics = self.metrics()

        @self.app.route('/skip/defaults')
        @metrics.counter('cnt_before', 'Counter before')
        @metrics.do_not_track()
        @metrics.counter('cnt_after', 'Counter after')
        def test():
            return 'OK'

        self.client.get('/skip/defaults')
        self.client.get('/skip/defaults')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('path', '/skip/defaults'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/skip/defaults'),
        )

        self.assertMetric('cnt_before_total', 2.0)
        self.assertMetric('cnt_after_total', 2.0)

    def test_exclude_all_wrapping(self):
        metrics = self.metrics()

        @self.app.route('/skip')
        @metrics.gauge('gauge_before', 'Gauge before')
        @metrics.counter('cnt_before', 'Counter before')
        @metrics.exclude_all_metrics()
        @metrics.counter('cnt_after', 'Counter after')
        @metrics.gauge('gauge_after', 'Gauge after')
        def test():
            return 'OK'

        self.client.get('/skip')
        self.client.get('/skip')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric('cnt_before_total', 0.0)
        self.assertMetric('cnt_after_total', 0.0)
        self.assertMetric('gauge_before', 0.0)
        self.assertMetric('gauge_after', 0.0)

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
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/test'),
            endpoint='/my-metrics'
        )

    def test_custom_metrics_decorator(self):
        invocations = list()

        def decorate_metrics(f):
            def decorated(*args):
                invocations.append('metrics')
                return f(*args)
            return decorated

        self.metrics(metrics_decorator=decorate_metrics)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        self.assertEqual(len(invocations), 0)

        self.assertMetric(
            'flask_http_request_total', '1.0',
            ('method', 'GET'), ('status', 200)
        )

        self.assertEqual(len(invocations), 1)

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
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            endpoint='/metrics'
        )

    def test_custom_defaults_prefix(self):
        self.assumeBeforeFlaskVersion('2.2.0')

        metrics = self.metrics(defaults_prefix='www')

        self.assertAbsent(
            'flask_exporter_info',
            ('version', metrics.version)
        )
        self.assertMetric(
            'www_exporter_info', '1.0',
            ('version', metrics.version)
        )

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'www_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'www_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_custom_defaults_prefix__F220(self):
        self.assumeMinimumFlaskVersion('2.2.0')

        metrics = self.metrics(defaults_prefix='www')

        @self.app.route('/test')
        def test():
            return 'OK'

        self.assertAbsent(
            'flask_exporter_info',
            ('version', metrics.version)
        )
        self.assertMetric(
            'www_exporter_info', '1.0',
            ('version', metrics.version)
        )

        self.client.get('/test')
        self.client.get('/test')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'www_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'www_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_no_defaults_prefix(self):
        metrics = self.metrics(defaults_prefix=NO_PREFIX)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.assertAbsent(
            'flask_exporter_info',
            ('version', metrics.version)
        )
        self.assertMetric(
            'exporter_info', '1.0',
            ('version', metrics.version)
        )

        self.client.get('/test')
        self.client.get('/test')
        self.client.get('/test')

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'http_request_total', '3.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_late_defaults_export(self):
        self.assumeBeforeFlaskVersion('2.2.0')

        metrics = self.metrics(export_defaults=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertAbsent(
            'flask_exporter_info',
            ('version', metrics.version)
        )
        self.assertAbsent(
            'late_exporter_info',
            ('version', metrics.version)
        )

        self.assertAbsent(
            'flask_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertAbsent(
            'late_http_request_total',
            ('method', 'GET'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/test'),
        )
        metrics.export_defaults(prefix='late')

        self.assertMetric(
            'late_exporter_info', '1.0',
            ('version', metrics.version)
        )

        self.client.get('/test')
        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'late_http_request_total', '3.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'late_http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/test'),
        )

    def test_late_defaults_export__F220(self):
        self.assumeMinimumFlaskVersion('2.2.0')

        metrics = self.metrics(export_defaults=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        metrics.export_defaults(prefix='late')

        self.assertMetric(
            'late_exporter_info', '1.0',
            ('version', metrics.version)
        )

        self.client.get('/test')
        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'late_http_request_total', '3.0',
            ('method', 'GET'), ('status', 200)
        )
        self.assertMetric(
            'late_http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_exceptions_total',
            ('method', 'GET'), ('path', '/test'),
        )

    def test_export_latencies_as_summary(self):
        self.assumeBeforeFlaskVersion('2.2.0')

        metrics = self.metrics(export_defaults=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertAbsent(
            'flask_http_request_duration_seconds_sum',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '+Inf'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

        metrics.export_defaults(latency_as_histogram=False)

        self.client.get('/test')
        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_duration_seconds_sum', '[0-9.e-]+',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '+Inf'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_export_latencies_as_summary__F220(self):
        self.assumeMinimumFlaskVersion('2.2.0')

        metrics = self.metrics(export_defaults=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        metrics.export_defaults(latency_as_histogram=False)

        self.client.get('/test')
        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_duration_seconds_sum', '[0-9.e-]+',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '3.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('le', '+Inf'), ('method', 'GET'), ('path', '/test'), ('status', 200)
        )

    def test_non_automatic_endpoint_registration(self):
        metrics = self.metrics(path=None)

        @self.app.route('/test')
        def test():
            return 'OK'

        metrics.register_endpoint('/manual/metrics')

        self.client.get('/test')

        no_metrics_response = self.client.get('/metrics')
        self.assertEqual(no_metrics_response.status_code, 404)

        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200),
            endpoint='/manual/metrics'
        )

    def test_latencies_as_summary(self):
        self.metrics(default_latency_as_histogram=False)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_duration_seconds_sum', '[0-9.e-]+',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200)
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

    def test_static_labels(self):
        metrics = self.metrics(static_labels={
            'app_name': 'Test-App',
            'api_version': 1
        })

        @self.app.route('/test')
        @metrics.counter('test_counter', 'Test Counter',
                         labels={'code': lambda r: r.status_code})
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )

        self.assertMetric(
            'test_counter_total', '2.0',
            ('code', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )
        self.assertMetric(
            'test_counter_created', '.',
            ('code', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )

        self.assertMetric(
            'flask_exporter_info', '',
            ('version', metrics.version)  # no default labels here
        )

    def test_static_labels_without_metric_labels(self):
        metrics = self.metrics(static_labels={
            'app_name': 'Test-App',
            'api_version': 1
        })

        @self.app.route('/test')
        @metrics.counter('test_counter', 'Test Counter')
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            ('app_name', 'Test-App'), ('api_version', 1)
        )

        self.assertMetric(
            'test_counter_total', '2.0',
            ('app_name', 'Test-App'), ('api_version', 1)
        )
        self.assertMetric(
            'test_counter_created', '.',
            ('app_name', 'Test-App'), ('api_version', 1)
        )

        self.assertMetric(
            'flask_exporter_info', '',
            ('version', metrics.version)  # no default labels here
        )

    def test_default_labels(self):
        metrics = self.metrics(
            static_labels={
                'static': 'testing'
            }, default_labels={
                'dm': lambda: request.method
            })

        @self.app.route('/test')
        @metrics.counter('test_counter', 'Test Counter',
                         labels={'code': lambda r: r.status_code})
        def test():
            return 'OK'

        self.client.get('/test')
        self.client.get('/test')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 200),
            ('static', 'testing'), ('dm', 'GET')
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/test'), ('status', 200),
            ('static', 'testing'), ('dm', 'GET')
        )

        self.assertMetric(
            'test_counter_total', '2.0',
            ('code', 200),
            ('static', 'testing'), ('dm', 'GET')
        )
        self.assertMetric(
            'test_counter_created', '.',
            ('code', 200),
            ('static', 'testing'), ('dm', 'GET')
        )

        self.assertMetric(
            'flask_exporter_info', '',
            ('version', metrics.version)  # no default labels here
        )
