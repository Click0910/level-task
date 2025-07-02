FROM bitnami/pytorch:1.13.1-debian-11-r29

USER root

RUN apt-get update && apt-get install -y \
    libsm6 libxrender1 libfontconfig1 libxext6 libglib2.0-0 \
    gcc binutils less git wget && \
    rm -rf /var/lib/apt/lists/*

ENV APP_DIR='/workers'
WORKDIR $APP_DIR
ENV PYTHONPATH="${APP_DIR}:${PYTHONPATH}"

COPY /requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --compile -r /tmp/requirements.txt && \
    rm -rf /tmp/* /var/tmp/*

ADD utils $APP_DIR/utils
ADD worker.py $APP_DIR/
ADD engine.py $APP_DIR/
ADD scripts $APP_DIR/scripts

RUN mkdir -p /workers/models

RUN wget https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets/resolve/main/dataset-tickets-multi-lang-4-20k.csv \
    -O /workers/dataset-tickets-multi-lang-4-20k.csv

RUN python $APP_DIR/scripts/train_model.py

EXPOSE 6379 5672
