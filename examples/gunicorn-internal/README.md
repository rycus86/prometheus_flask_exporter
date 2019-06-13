# Gunicorn example (internal metrics endpoint)

This [Gunicorn](https://gunicorn.org/) example has a sample app in [server.py](server.py) with
multiprocessing enabled for metrics collection.
In practise, this means the individual forks metrics
will be combined, and the metrics endpoint from any of them
should include the global stats.

This example exposes the metrics on an individual internal HTTP endpoint, but still within the same Gunicorn server, also configured by the [config.py](config.py) file.

## Thanks

Huge thanks for [@Miouge1](https://github.com/Miouge1) for
bringing this to my attention in [prometheus_flask_exporter#15](https://github.com/rycus86/prometheus_flask_exporter/issues/15) !
