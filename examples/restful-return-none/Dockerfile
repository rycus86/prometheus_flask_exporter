FROM python:3.8-alpine

RUN apk add --no-cache curl && pip install flask flask_restful prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/restful-return-none/server.py /var/flask/example.py
WORKDIR /var/flask

CMD python /var/flask/example.py
