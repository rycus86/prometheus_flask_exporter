# Gunicorn example

This [Gunicorn](https://gunicorn.org/) example has a sample app in [server.py](server.py) with
multiprocessing enabled for metrics collection.

This example checks that exception metrics are not counted twice due to both the Flask `after_request`
and `teardown_request` callbacks seeing that request.

## Thanks

Huge thanks for [@idlefella](https://github.com/idlefella) for
bringing this to my attention in [prometheus_flask_exporter#113](https://github.com/rycus86/prometheus_flask_exporter/issues/113) !
