FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y \
	supervisor python3-dev python3-pip

WORKDIR /usr/src/
COPY . .

RUN pip3 install poetry psycopg2-binary # TODO: Wait fix of poetry to remove psycopg2-binary
RUN poetry install --only main
COPY ./supervisor.conf /etc/supervisor/conf.d/
RUN chmod a+x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"] 
