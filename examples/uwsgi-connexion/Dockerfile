FROM python:3.8-alpine

RUN apk add --no-cache gcc musl-dev linux-headers

RUN apk add --no-cache curl && pip install flask connexion uwsgi prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/uwsgi-connexion /var/flask
WORKDIR /var/flask

ENV prometheus_multiproc_dir /tmp
ENV METRICS_PORT 9200

CMD uwsgi --http 0.0.0.0:4000 --module main:app --master --processes 4 --threads 2