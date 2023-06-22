## Base dependencies ########################################################################
ARG GO_VERSION=1.20
ARG PROTOBUF_VERSION=3.15.8

FROM golang:${GO_VERSION} as base

ARG PROTOBUF_VERSION

# This image is only for building, so we run as root
WORKDIR /src

COPY requirements_test.txt /src/requirements_test.txt
RUN true && \
    apt-get update -y && \
    apt-get install make git -y && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    apt-get install -y \
        unzip \
        python3.9 \
        python3-pip && \
    apt-get upgrade -y && \
    pip install pip --upgrade && \
    pip install twine pre-commit && \
    pip3 install -r /src/requirements_test.txt && \
    true

# Install protoc
RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip
RUN unzip protoc-3.15.8-linux-x86_64.zip -d /protoc
ENV PATH=${PATH}:/protoc/bin

## Test ########################################################################
FROM base as test

# Run unit tests
COPY . /src
RUN true && \
    ./scripts/run_tests.sh && \
    RELEASE_DRY_RUN=true RELEASE_VERSION=0.0.0 \
        ./scripts/publish.sh && \
    ./scripts/fmt.sh && \
    true

## Release #####################################################################
#
# This phase builds the release and publishes it to pypi
##
FROM test as release
ARG PYPI_TOKEN
ARG RELEASE_VERSION
ARG RELEASE_DRY_RUN
RUN ./scripts/publish.sh

## Release Test ################################################################
#
# This phase installs the indicated version from PyPi and runs the unit tests
# against the installed version.
##
FROM base as release_test
ARG RELEASE_VERSION
ARG RELEASE_DRY_RUN
COPY ./tests /src/tests
COPY ./scripts/run_tests.sh /src/scripts/run_tests.sh
COPY ./scripts/install_release.sh /src/scripts/install_release.sh
RUN true && \
    ./scripts/install_release.sh && \
    ./scripts/run_tests.sh && \
    true