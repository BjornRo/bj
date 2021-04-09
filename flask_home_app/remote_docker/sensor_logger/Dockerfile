FROM python:slim

ENV CONTAINER_HOME=/usr/src/app
ENV TZ=Europe/Stockholm

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

#RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
RUN echo "Europe/Stockholm" >  /etc/timezone

CMD ["python3", "__main__.py"]