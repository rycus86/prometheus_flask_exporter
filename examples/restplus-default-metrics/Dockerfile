FROM python:3.8-alpine

# werkzeug needs to be pinned due to https://github.com/python-restx/flask-restx/issues/460
RUN apk add --no-cache curl && pip install flask flask-restx prometheus_client werkzeug==2.0.*

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/restplus-default-metrics/server.py /var/flask/example.py
WORKDIR /var/flask

CMD python /var/flask/example.py
