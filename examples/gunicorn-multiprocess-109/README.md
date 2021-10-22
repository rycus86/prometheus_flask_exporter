# Gunicorn example

This [Gunicorn](https://gunicorn.org/) example has a sample app in [server.py](server.py) with
multiprocessing enabled for metrics collection.
In practise, this means the individual forks metrics
will be combined, and the metrics endpoint from any of them
should include the global stats.

This example exposes the metrics on an individual endpoint, managed by [prometheus_client](https://github.com/prometheus/client_python#multiprocess-mode-gunicorn), started only on the master process, configured in the [config.py](config.py) file.

## Thanks

Huge thanks for [@focabr](https://github.com/focabr) for
bringing this to my attention in [prometheus_flask_exporter#109](https://github.com/rycus86/prometheus_flask_exporter/issues/109) !
