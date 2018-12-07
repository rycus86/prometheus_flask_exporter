import os

from prometheus_client import multiprocess, CollectorRegistry
from prometheus_client import start_wsgi_server

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)


def when_ready(server):
    start_wsgi_server(int(os.getenv('METRICS_PORT')), registry=registry)
    # or alternatively:
    #   start_http_server(int(os.getenv('METRICS_PORT')), registry=registry)


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
