FROM totem/python-base:3.4-trusty-b2

ADD requirements.txt /opt/
RUN pip install -r /opt/requirements.txt

ADD . /opt/configservice
RUN chmod -R +x /opt/configservice/bin

EXPOSE 9003

WORKDIR /opt/configservice

ENTRYPOINT ["/opt/configservice/bin/run.sh"]