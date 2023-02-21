import logging
import os
import threading
import time
import traceback
import gunicorn
import gunicorn.app.base

from flask import Flask
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from pebble import concurrent
from prometheus_client.core import REGISTRY, InfoMetricFamily
from concurrent.futures import TimeoutError
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
from prometheus_client import Counter


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


class CustomCollector:
    def collect(self):
        info = InfoMetricFamily('xxxx', 'xxxxxx')
        info.add_metric(labels='version',
                        value={
                            'version': 'xxxxx',
                            'loglevel': 'xxx',
                            'root': 'xxxx',
                            'workers': 'xxxx',
                            'ip': 'xxxxx',
                            'port': 'xxx',
                            'config_name': 'xxxx',
                            'mode': 'xx',
                            'debug': 'xxx',
                            'node': 'xxx',
                            'pod': 'xxx',
                            'pid': str(os.getpid())
                        }
                        )
        yield info


thread_sum = Counter('thread_count',
                     'Total count of the thread application.',
                     ['pod', 'node', 'mode'])


def add_metric_thread(count=False):
    if count:
        thread_sum.labels(mode='mode', node='NODE', pod='POD').inc(count)
    else:
        thread_sum.labels(mode='mode', node='NODE', pod='POD')


def when_ready(server):
    GunicornInternalPrometheusMetrics.start_http_server_when_ready(8080)


def child_exit(server, worker):
    GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)


def thread_function():
    @concurrent.process(timeout=300)
    def job():
        open_threads = threading.active_count()
        add_metric_thread(open_threads)
        print(f'How thread Open .: {open_threads}')
        print(f'run_threaded - {threading.current_thread()}')
        time.sleep(20)

    while True:
        time.sleep(10)

        future = job()
        try:
            future.result()  # blocks until results are ready
        except TimeoutError as error:
            logging.error(f'Job timeout of 5 minute {error.args[1]}')
        except Exception:
            logging.error(f' job - {traceback.format_exc()}')


def init():
    print('Thread - starting')
    thread = threading.Thread(target=thread_function, daemon=True)
    thread.start()
    add_metric_thread()


def create_app():
    app = Flask(__name__)
    metrics.init_app(app)

    # Add prometheus wsgi middleware to route /metrics requests
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/metrics': make_wsgi_app(registry=REGISTRY)
    })

    init()

    @app.route('/test')
    def main():
        return 'Ok'

    return app


REGISTRY.register(CustomCollector())

metrics = GunicornInternalPrometheusMetrics.for_app_factory(
    path='/metrics',
    static_labels={'node': 'xxx', 'pod': 'xx', 'version': 'xx'},
    registry=REGISTRY
)

if __name__ == '__main__':
    options = {
        'bind': ['0.0.0.0:9200'],
        'workers': 4,
        'loglevel': 'debug'
    }
    std_app = StandaloneApplication(create_app(), options)
    std_app.run()
