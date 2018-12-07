# uWSGI example

This [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) example has a sample app in [server.py](server.py) with
multiprocessing enabled for metrics collection.
In practise, this means the individual forks metrics
will be combined, and the metrics endpoint from any of them
should include the global stats.

This example exposes the metrics on an individual endpoint, managed by [prometheus_client](https://github.com/prometheus/client_python#multiprocess-mode-gunicorn), started only on the master process.

## Thanks

Huge thanks for [@Miouge1](https://github.com/Miouge1) for
bringing this to my attention in [prometheus_flask_exporter#15](https://github.com/rycus86/prometheus_flask_exporter/issues/15) !
