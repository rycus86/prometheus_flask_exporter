FROM python:3.7-alpine

RUN apk add --no-cache curl && pip install flask flask_restful prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/restful-with-blueprints/server.py /var/flask/example.py
WORKDIR /var/flask

CMD python /var/flask/example.py
