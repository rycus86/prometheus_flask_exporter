import warnings

from unittest_helper import BaseTestCase


class GroupByTest(BaseTestCase):

    def test_group_by_path_default(self):
        self.metrics()

        @self.app.route('/<url>')
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/default1')
        self.client.get('/default2')
        self.client.get('/default3')

        for path in ('/default1', '/default2', '/default3'):
            self.assertMetric(
                'flask_http_request_duration_seconds_bucket', '1.0',
                ('path', path), ('status', 200),
                ('le', '+Inf'), ('method', 'GET'),
                endpoint='/metrics'
            )
            self.assertMetric(
                'flask_http_request_duration_seconds_count', '1.0',
                ('path', path), ('status', 200), ('method', 'GET'),
                endpoint='/metrics'
            )

    def test_group_by_path_default_with_summaries(self):
        self.metrics(default_latency_as_histogram=False)

        @self.app.route('/<url>')
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/default1')
        self.client.get('/default2')
        self.client.get('/default3')

        for path in ('/default1', '/default2', '/default3'):
            self.assertMetric(
                'flask_http_request_duration_seconds_sum', '[0-9.e-]+',
                ('path', path), ('status', 200), ('method', 'GET'),
                endpoint='/metrics'
            )
            self.assertMetric(
                'flask_http_request_duration_seconds_count', '1.0',
                ('path', path), ('status', 200), ('method', 'GET'),
                endpoint='/metrics'
            )

    def test_group_by_path(self):
        self.metrics(group_by='path')

        @self.app.route('/<url>')
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/test1')
        self.client.get('/test2')
        self.client.get('/test3')

        for path in ('/test1', '/test2', '/test3'):
            self.assertMetric(
                'flask_http_request_duration_seconds_bucket', '1.0',
                ('path', path), ('status', 200),
                ('le', '+Inf'), ('method', 'GET'),
                endpoint='/metrics'
            )
            self.assertMetric(
                'flask_http_request_duration_seconds_count', '1.0',
                ('path', path), ('status', 200), ('method', 'GET'),
                endpoint='/metrics'
            )

    def test_group_by_rule(self):
        self.metrics(group_by='url_rule')

        @self.app.route('/test/<item>')
        def first_test_endpoint(item):
            return item + ' is OK'

        @self.app.route('/get/<sample>')
        def second_test_endpoint(sample):
            return sample + ' is OK'

        self.client.get('/test/1')
        self.client.get('/test/2')
        self.client.get('/get/1')

        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '2.0',
            ('url_rule', '/test/<item>'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '2.0',
            ('url_rule', '/test/<item>'), ('status', 200), ('method', 'GET'),
            endpoint='/metrics'
        )

        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '1.0',
            ('url_rule', '/get/<sample>'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '1.0',
            ('url_rule', '/get/<sample>'), ('status', 200), ('method', 'GET'),
            endpoint='/metrics'
        )

    def test_group_by_endpoint(self):
        self.metrics(group_by='endpoint')

        @self.app.route('/<url>')
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/test')
        self.client.get('/test2')
        self.client.get('/test3')

        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '3.0',
            ('endpoint', 'a_test_endpoint'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '3.0',
            ('endpoint', 'a_test_endpoint'), ('status', 200), ('method', 'GET'),
            endpoint='/metrics'
        )

        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('path', '/test'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )

    def test_group_by_endpoint_deprecated(self):
        warnings.filterwarnings('once', category=DeprecationWarning)

        with warnings.catch_warnings(record=True) as w:
            self.metrics(group_by_endpoint=True)

        # make sure we have the deprecation warning for this
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0].category, DeprecationWarning)
        self.assertIn('group_by_endpoint', str(w[0].message))

        @self.app.route('/<url>')
        def a_legacy_endpoint(url):
            return url + ' is OK'

        self.client.get('/test')
        self.client.get('/test2')
        self.client.get('/test3')

        self.assertMetric(
            'flask_http_request_duration_seconds_bucket', '3.0',
            ('endpoint', 'a_legacy_endpoint'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )
        self.assertMetric(
            'flask_http_request_duration_seconds_count', '3.0',
            ('endpoint', 'a_legacy_endpoint'), ('status', 200), ('method', 'GET'),
            endpoint='/metrics'
        )

        self.assertAbsent(
            'flask_http_request_duration_seconds_bucket',
            ('path', '/test'), ('status', 200),
            ('le', '+Inf'), ('method', 'GET'),
            endpoint='/metrics'
        )

    def test_group_by_deprecated_late_warning(self):
        warnings.filterwarnings('once', category=DeprecationWarning)

        with warnings.catch_warnings(record=True) as initial:
            metrics = self.metrics(export_defaults=False)

        self.assertEqual(len(initial), 0)

        with warnings.catch_warnings(record=True) as w:
            metrics.export_defaults(group_by_endpoint=True)

        # make sure we have the deprecation warning for this
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0].category, DeprecationWarning)
        self.assertIn('group_by_endpoint', str(w[0].message))

    def test_group_by_full_path(self):
        self.metrics(group_by='full_path')

        @self.app.route('/<url>')
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/test?x=1')
        self.client.get('/test?x=2')
        self.client.get('/test?x=3')

        for path in ('/test?x=1', '/test?x=2', '/test?x=3'):
            self.assertMetric(
                'flask_http_request_duration_seconds_bucket', '1.0',
                ('full_path', path), ('status', 200),
                ('le', '+Inf'), ('method', 'GET'),
                endpoint='/metrics'
            )
            self.assertMetric(
                'flask_http_request_duration_seconds_count', '1.0',
                ('full_path', path), ('status', 200), ('method', 'GET'),
                endpoint='/metrics'
            )

    def test_group_by_func(self):
        def composite(r):
            return '%s::%s >> %s' % (
                r.method,
                r.path,
                r.args.get('type', 'none')
            )

        self.metrics(group_by=composite)

        @self.app.route('/<url>', methods=['GET', 'POST'])
        def a_test_endpoint(url):
            return url + ' is OK'

        self.client.get('/sample?type=A')
        self.client.get('/sample?type=Beta')
        self.client.post('/plain')

        for value in ('GET::/sample >> A', 'GET::/sample >> Beta', 'POST::/plain >> none'):
            self.assertMetric(
                'flask_http_request_duration_seconds_bucket', '1.0',
                ('composite', value), ('status', 200),
                ('le', '+Inf'), ('method', value.split('::').pop(0)),
                endpoint='/metrics'
            )
            self.assertMetric(
                'flask_http_request_duration_seconds_count', '1.0',
                ('composite', value), ('status', 200), ('method', value.split('::').pop(0)),
                endpoint='/metrics'
            )

    def test_group_by_lambda_is_not_supported(self):
        try:
            self.metrics(group_by=lambda r: '%s-%s' % (r.method, r.path))
            self.fail('Expected to fail on grouping by lambda')
        except Exception as ex:
            self.assertIn('invalid label', str(ex).lower())
