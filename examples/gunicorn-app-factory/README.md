# Gunicorn example (app factory pattern)

This [Gunicorn](https://gunicorn.org/) example has a sample app in [server.py](server.py) with
multiprocessing enabled for metrics collection.
In practise, this means the individual forks metrics
will be combined, and the metrics endpoint from any of them
should include the global stats.

This example exposes the metrics on an individual internal HTTP endpoint, but still within the same Gunicorn server, also configured by the [config.py](config.py) file. The app is configured using the [app factory pattern](http://flask.pocoo.org/docs/1.0/patterns/appfactories/)

## Thanks

Huge thanks for [@mamor1](https://github.com/mamor1) for
bringing this to my attention in [prometheus_flask_exporter#33](https://github.com/rycus86/prometheus_flask_exporter/issues/33) !
