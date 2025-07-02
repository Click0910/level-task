FROM python:3.11-slim

COPY /requirements.txt /tmp/requirements.txt

ENV APP_DIR='/workers'
WORKDIR $APP_DIR

RUN apt-get update && apt-get install -y libsndfile1 gcc
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --compile -r /tmp/requirements.txt && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*

ADD /app $APP_DIR/app/
ADD worker.py $APP_DIR/
ADD scripts $APP_DIR/scripts/

EXPOSE 6379 5672
