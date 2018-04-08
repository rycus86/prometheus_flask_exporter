# WSGI example

This example has a sample app in [app.py](app.py) with
multiprocessing enabled for metrics collection.
In practise, this means the individual forks metrics
will be combined, and the metrics endpoint from any of them
should include the global stats.

## Thanks

Huge thanks for [@thatcher](https://github.com/thatcher) for
bringing this to my attention, and for the investigation he's
done in [prometheus_flask_exporter#5](https://github.com/rycus86/prometheus_flask_exporter/issues/5) !
