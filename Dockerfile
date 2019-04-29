FROM python:3.6
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

# update apt-get
RUN apt-get update -y && apt-get upgrade -y

# Install Nodejs 8
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get install -y nodejs

# install aws-cli
RUN pip install awscli

# install boto3
RUN pip install boto3

# install pipenv
RUN pip install pipenv

# install serverless framework
RUN npm install -g serverless

# set aws key
RUN sls config credentials --provider aws --key $AWS_ACCESS_KEY_ID --secret $AWS_SECRET_ACCESS_KEY

# install node_modules from project's packeage.json
RUN mkdir -p /app
WORKDIR /app
ADD app/package.json /app/package.json
RUN set -x && npm install