FROM httpd

RUN apt-get update \
    && apt-get install --no-install-recommends -y python python-dev python-pip gcc \
    && pip install mod_wsgi

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD httpd.conf /usr/local/apache2/conf/httpd.conf
ADD app.py wsgi.py /var/flask/
