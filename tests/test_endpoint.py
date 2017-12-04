from unittest_helper import BaseTestCase

import time

try:
    from urllib2 import urlopen
except:
    # Python 3
    from urllib.request import urlopen


class EndpointTest(BaseTestCase):
    def test_restricted(self):
        metrics = self.metrics()

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

