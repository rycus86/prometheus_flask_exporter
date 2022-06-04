import time

import werkzeug.exceptions
from flask import request, abort
from unittest_helper import BaseTestCase

try:
    from urllib2 import urlopen
except ImportError:
    # Python 3
    from urllib.request import urlopen


class EndpointTest(BaseTestCase):
    def test_restricted(self):
        self.metrics()

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        response = self.client.get('/metrics')

        self.assertIn('flask_exporter_info', str(response.data))
        self.assertIn('flask_http_request_total', str(response.data))
        self.assertIn('flask_http_request_duration_seconds', str(response.data))

        response = self.client.get('/metrics?name[]=flask_exporter_info')

        self.assertIn('flask_exporter_info', str(response.data))
        self.assertNotIn('flask_http_request_total', str(response.data))
        self.assertNotIn('flask_http_request_duration_seconds', str(response.data))

        response = self.client.get('/metrics'
                                   '?name[]=flask_http_request_duration_seconds_bucket'
                                   '&name[]=flask_http_request_duration_seconds_count'
                                   '&name[]=flask_http_request_duration_seconds_sum')

        self.assertNotIn('flask_exporter_info', str(response.data))
        self.assertNotIn('flask_http_request_total', str(response.data))
        self.assertIn('flask_http_request_duration_seconds_bucket', str(response.data))
        self.assertIn('flask_http_request_duration_seconds_count', str(response.data))
        self.assertIn('flask_http_request_duration_seconds_sum', str(response.data))

    def test_generate_metrics_content(self):
        metrics = self.metrics(path=None)

        @self.app.route('/test')
        def test():
            return 'OK'

        self.client.get('/test')

        response = self.client.get('/metrics')
        self.assertEqual(404, response.status_code)

        response_data, _ = metrics.generate_metrics()

        self.assertIn('flask_exporter_info', response_data)
        self.assertIn('flask_http_request_total', response_data)
        self.assertIn('flask_http_request_duration_seconds', response_data)

        response_data, _ = metrics.generate_metrics(names=['flask_exporter_info'])

        self.assertIn('flask_exporter_info', response_data)
        self.assertNotIn('flask_http_request_total', response_data)
        self.assertNotIn('flask_http_request_duration_seconds', response_data)

        response_data, _ = metrics.generate_metrics(names=[
            'flask_http_request_duration_seconds_bucket',
            'flask_http_request_duration_seconds_count',
            'flask_http_request_duration_seconds_sum'
        ])

        self.assertNotIn('flask_exporter_info', response_data)
        self.assertNotIn('flask_http_request_total', response_data)
        self.assertIn('flask_http_request_duration_seconds_bucket', response_data)
        self.assertIn('flask_http_request_duration_seconds_count', response_data)
        self.assertIn('flask_http_request_duration_seconds_sum', response_data)

    def test_http_server(self):
        metrics = self.metrics()

        metrics.start_http_server(32001)
        metrics.start_http_server(32002, endpoint='/test/metrics')
        metrics.start_http_server(32003, host='127.0.0.1')

        def wait_for_startup():
            for _ in range(10):
                try:
                    urlopen('http://localhost:32001/metrics')
                    urlopen('http://localhost:32002/test/metrics')
                    urlopen('http://localhost:32003/metrics')
                    break
                except:
                    time.sleep(0.5)

        wait_for_startup()

        response = urlopen('http://localhost:32001/metrics')

        self.assertEqual(response.getcode(), 200)
        self.assertIn('flask_exporter_info', str(response.read()))

        response = urlopen('http://localhost:32002/test/metrics')

        self.assertEqual(response.getcode(), 200)
        self.assertIn('flask_exporter_info', str(response.read()))

        response = urlopen('http://localhost:32003/metrics')

        self.assertEqual(response.getcode(), 200)
        self.assertIn('flask_exporter_info', str(response.read()))

    def test_http_status_enum(self):
        try:
            from http import HTTPStatus
        except ImportError:
            self.skipTest('http.HTTPStatus is not available')

        metrics = self.metrics()

        @self.app.route('/no/content')
        def no_content():
            import http
            return {}, http.HTTPStatus.NO_CONTENT

        self.client.get('/no/content')
        self.client.get('/no/content')

        self.assertMetric(
            'flask_http_request_total', '2.0',
            ('method', 'GET'), ('status', 204)
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('method', 'GET'), ('path', '/no/content'), ('status', 204)
        )

    def test_abort(self):
        metrics = self.metrics()

        @self.app.route('/error')
        @metrics.summary('http_index_requests_by_status',
                         'Request latencies by status',
                         labels={'status': lambda r: r.status_code})
        @metrics.histogram('http_index_requests_by_status_and_path',
                           'Index requests latencies by status and path',
                           labels={
                               'status': lambda r: r.status_code,
                               'path': lambda: request.path
                           })
        def throw_error():
            return abort(503)

        self.client.get('/error')

        self.assertMetric('http_index_requests_by_status_count', 1.0, ('status', 503))
        self.assertMetric('http_index_requests_by_status_sum', '.', ('status', 503))

        self.assertMetric(
            'http_index_requests_by_status_and_path_count', 1.0,
            ('status', 503), ('path', '/error')
        )
        self.assertMetric(
            'http_index_requests_by_status_and_path_sum', '.',
            ('status', 503), ('path', '/error')
        )
        self.assertMetric(
            'http_index_requests_by_status_and_path_bucket', 1.0,
            ('status', 503), ('path', '/error'), ('le', 0.5)
        )
        self.assertMetric(
            'http_index_requests_by_status_and_path_bucket', 1.0,
            ('status', 503), ('path', '/error'), ('le', 10.0)
        )

    def test_exception(self):
        metrics = self.metrics()

        @self.app.route('/exception')
        @metrics.summary('http_with_exception',
                         'Tracks the method raising an exception',
                         labels={'status': lambda r: r.status_code})
        def raise_exception():
            raise NotImplementedError('On purpose')

        try:
            self.client.get('/exception')
        except NotImplementedError:
            pass

        self.assertMetric('http_with_exception_count', 1.0, ('status', 500))
        self.assertMetric('http_with_exception_sum', '.', ('status', 500))

    def test_abort_before(self):
        @self.app.before_request
        def before_request():
            if request.path == '/metrics':
                return

            raise abort(400)

        self.metrics()

        self.client.get('/abort/before')
        self.client.get('/abort/before')

        self.assertMetric(
            'flask_http_request_total', 2.0,
            ('method', 'GET'), ('status', 400)
        )

    def test_error_handler(self):
        metrics = self.metrics()

        @self.app.errorhandler(NotImplementedError)
        def not_implemented_handler(e):
            return 'Not implemented', 400

        @self.app.errorhandler(werkzeug.exceptions.Conflict)
        def handle_conflict(e):
            return 'Bad request for conflict', 400, {'X-Original': e.code}

        @self.app.route('/exception')
        @metrics.summary('http_with_exception',
                         'Tracks the method raising an exception',
                         labels={'status': lambda r: r.status_code})
        def raise_exception():
            raise NotImplementedError('On purpose')

        @self.app.route('/conflict')
        @metrics.summary('http_with_code',
                         'Tracks the error with the original code',
                         labels={'status': lambda r: r.status_code,
                                 'code': lambda r: r.headers.get('X-Original', -1)})
        def conflicts():
            abort(409)

        for _ in range(3):
            self.client.get('/exception')

        for _ in range(7):
            self.client.get('/conflict')

        self.assertMetric('http_with_exception_count', 3.0, ('status', 400))
        self.assertMetric('http_with_exception_sum', '.', ('status', 400))

        self.assertMetric('http_with_code_count', 7.0, ('status', 400), ('code', 409))
        self.assertMetric('http_with_code_sum', '.', ('status', 400), ('code', 409))

    def test_error_no_handler(self):
        self.metrics()

        @self.app.route('/exception')
        def raise_exception():
            raise NotImplementedError('On purpose')

        for _ in range(5):
            try:
                self.client.get('/exception')
            except NotImplementedError:
                pass

        self.assertMetric('flask_http_request_total', 5.0, ('method', 'GET'), ('status', 500))
        self.assertMetric(
            'flask_http_request_duration_seconds_count', 5.0,
            ('method', 'GET'), ('status', 500), ('path', '/exception')
        )

    def test_named_endpoint(self):
        metrics = self.metrics()

        @self.app.route('/testing', endpoint='testing_endpoint')
        @metrics.summary('requests_by_status',
                         'Request latencies by status',
                         labels={'status': lambda r: r.status_code})
        def testing():
            return 'OK'

        for _ in range(5):
            self.client.get('/testing')

        self.assertMetric('requests_by_status_count', 5.0, ('status', 200))
        self.assertMetric('requests_by_status_sum', '.', ('status', 200))

    def test_track_multiple_endpoints(self):
        metrics = self.metrics()

        test_request_counter = metrics.counter(
            'test_counter', 'Request counter for tests',
            labels={'path': lambda: request.path}
        )

        @self.app.route('/first')
        @test_request_counter
        def first():
            return 'OK'

        @self.app.route('/second')
        @test_request_counter
        def second():
            return 'OK'

        for _ in range(5):
            self.client.get('/first')
            self.client.get('/second')

        self.assertMetric(
            'flask_http_request_total', 10.0,
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric(
            'test_counter_total', 5.0, ('path', '/first')
        )
        self.assertMetric(
            'test_counter_total', 5.0, ('path', '/second')
        )

    def test_track_more_defaults(self):
        metrics = self.metrics()

        @self.app.route('/first')
        def first():
            return 'OK'

        @self.app.route('/second')
        def second():
            return 'OK'

        metrics.register_default(
            metrics.counter(
                'test_counter', 'Request counter for tests',
                labels={'path': lambda: request.path}
            ),
            metrics.summary(
                'test_summary', 'Request summary for tests',
                labels={'path': lambda: request.path}
            )
        )

        for _ in range(5):
            self.client.get('/first')
            self.client.get('/second')

        self.assertMetric(
            'flask_http_request_total', 10.0,
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric(
            'test_counter_total', 5.0, ('path', '/first')
        )
        self.assertMetric(
            'test_counter_total', 5.0, ('path', '/second')
        )

    def test_excluded_endpoints(self):
        self.metrics(excluded_paths='/exc')

        class RequestCounter(object):
            value = 0

        @self.app.route('/included')
        def included():
            RequestCounter.value += 1
            return 'OK'

        @self.app.route('/excluded')
        def excluded():
            RequestCounter.value += 1
            return 'OK'

        for _ in range(5):
            self.client.get('/included')
            self.client.get('/excluded')

        self.assertEqual(10, RequestCounter.value)

        self.assertMetric(
            'flask_http_request_total', 5.0,
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric(
            'flask_http_request_duration_seconds_count', 5.0,
            ('method', 'GET'), ('status', 200), ('path', '/included')
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('status', 200), ('path', '/excluded')
        )

    def test_multiple_excluded_endpoints(self):
        self.metrics(excluded_paths=[
            '/exc/one',
            '/exc/t.*'
        ])

        class RequestCounter(object):
            value = 0

        @self.app.route('/included')
        def included():
            RequestCounter.value += 1
            return 'OK'

        @self.app.route('/exc/one')
        def excluded_one():
            RequestCounter.value += 1
            return 'OK'

        @self.app.route('/exc/two')
        def excluded_two():
            RequestCounter.value += 1
            return 'OK'

        for _ in range(5):
            self.client.get('/included')
            self.client.get('/exc/one')
            self.client.get('/exc/two')

        self.assertEqual(15, RequestCounter.value)

        self.assertMetric(
            'flask_http_request_total', 5.0,
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric(
            'flask_http_request_duration_seconds_count', 5.0,
            ('method', 'GET'), ('status', 200), ('path', '/included')
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('status', 200), ('path', '/exc/one')
        )
        self.assertAbsent(
            'flask_http_request_duration_seconds_count',
            ('method', 'GET'), ('status', 200), ('path', '/exc/two')
        )

    def test_exclude_paths_from_user_metrics(self):
        metrics = self.metrics(excluded_paths='/excluded', exclude_user_defaults=True)

        @self.app.route('/included')
        def included():
            return 'OK'

        @self.app.route('/excluded')
        def excluded():
            return 'OK'

        metrics.register_default(
            metrics.counter(
                name='by_path_counter',
                description='Request count by path',
                labels={'path': lambda: request.path}
            )
        )

        for _ in range(5):
            self.client.get('/included')
            self.client.get('/excluded')

        self.assertMetric(
            'flask_http_request_total', 5.0,
            ('method', 'GET'), ('status', 200)
        )

        self.assertMetric(
            'by_path_counter_total', 5.0,
            ('path', '/included')
        )
        self.assertAbsent(
            'by_path_counter_total',
            ('path', '/excluded')
        )
