FROM python:3.8-slim AS bot

ENV BOT_TOKEN="INSERT BOT TOKEN"

RUN apt-get update
RUN apt-get install -y python3 python3-pip python-dev build-essential python3-venv ffmpeg

RUN mkdir -p /codebase
ADD . /codebase

WORKDIR /codebase

RUN pip3 install -r requirements.txt

CMD python3 tyttabot.py