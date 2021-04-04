FROM memcached:alpine

RUN rm /etc/memcached.conf
COPY memcached.conf /etc/


FROM python:alpine

ENV CONTAINER_HOME=/usr/src/app

ADD __main__.py $CONTAINER_HOME

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "__main__.py"]