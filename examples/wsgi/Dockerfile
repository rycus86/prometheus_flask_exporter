FROM httpd

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        python3 python3-dev python3-pip python3-venv \
        libapr1-dev libaprutil1-dev gcc

WORKDIR /usr/local/apache2

ADD examples/wsgi/requirements.txt /tmp/requirements.txt
ADD . /tmp/latest

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install mod_wsgi \
    && pip install -r /tmp/requirements.txt \
    && pip install -e /tmp/latest --upgrade

ADD examples/wsgi/httpd.conf /usr/local/apache2/conf/httpd.conf
ADD examples/wsgi/app.py examples/wsgi/wsgi.py /var/flask/
