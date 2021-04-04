FROM python:alpine

ENV CONTAINER_HOME=/var/www

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
