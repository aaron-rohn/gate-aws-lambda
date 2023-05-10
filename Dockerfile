FROM opengatecollaboration/gate

RUN yum install -y libtool autoconf automake python39 python39-pip
RUN pip3.9 install awslambdaric boto3

#COPY aws-lambda-rie aws-lambda-rie
COPY app.py app.py

#ENTRYPOINT ["aws-lambda-rie"]
#CMD ["/usr/bin/python3.9", "-m", "awslambdaric", "app.handler"]

ENTRYPOINT ["/usr/bin/python3.9"]
CMD ["-m", "awslambdaric", "app.handler"]
