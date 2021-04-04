FROM python:alpine

ENV CONTAINER_HOME=/usr/src/app

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
RUN apk update && \
    apk add --no-cache tzdata
RUN echo "Europe/Stockholm" >  /etc/timezone

CMD ["python3", "__main__.py"]