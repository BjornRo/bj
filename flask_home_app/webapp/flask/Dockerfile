FROM python:buster

ENV CONTAINER_HOME=/var/www
ENV PYTHONUNBUFFERED=1

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt