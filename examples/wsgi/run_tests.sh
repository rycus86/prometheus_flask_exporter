#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs wsgi-sample
    docker rm -f wsgi-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t wsgi-sample ../../. > /dev/null || _fail
docker run -d --name wsgi-sample -p 8889:80 wsgi-sample > /dev/null || _fail

echo 'Waiting for the server to start...'

for _ in $(seq 1 10); do
    if curl -fs http://localhost:8889/ping > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s http://localhost:8889/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:8889/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/test",status="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f wsgi-sample > /dev/null
echo 'OK, all done'