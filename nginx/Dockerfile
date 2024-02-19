FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y nginx

COPY ./nginx.conf /etc/nginx/nginx.conf

CMD ["nginx", "-g daemon off;"]
