FROM python:slim

ENV CONTAINER_HOME=/usr/src/app
ENV TZ=Europe/Stockholm

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

RUN apt-get update && apt-get -y install gcc g++
RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
RUN echo "Europe/Stockholm" >  /etc/timezone

#RUN mkdir -p /devices
#RUN ln -s /devices /sys/bus/w1/devices/
EXPOSE 42660
CMD ["python3", "__main__.py"]