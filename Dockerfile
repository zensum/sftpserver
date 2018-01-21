FROM python:3.6.4-alpine3.7

RUN apk add --update \
openssl-dev \
libffi-dev \
python-dev \
build-base \
&& rm -rf /var/cache/apk/*

# -- Install Pipenv:
RUN set -ex && pip install pipenv --upgrade

# -- Install Application into container:
RUN set -ex && mkdir /app

WORKDIR /app

# -- Adding Pipfiles
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

# -- Install dependencies:
RUN set -ex && pipenv install --deploy --system

COPY sftpserver /app/sftpserver

CMD ["python", "-m", "sftpserver"]
