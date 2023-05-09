## deps ########################################################################
ARG PYTHON_TAG=py39
ARG OS=ubi8
ARG BASE_IMAGE_TAG=latest
ARG GO_VERSION=1.19
ARG PROTOBUF_VERSION=3.15.8

FROM golang:${GO_VERSION} as development

ARG PROTOBUF_VERSION
COPY requirements_test.txt /requirements_test.txt
RUN true && \
    apt-get update && \
    apt-get install -y \
        unzip \
        python3.9 \
        python3-pip && \
    apt-get upgrade -y && \
    pip3 install -r /requirements_test.txt && \
    true

ARG PROTOBUF_VERSION=3.15.8
RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip
RUN unzip protoc-3.15.8-linux-x86_64.zip -d /protoc
ENV PATH=${PATH}:/protoc/bin

## build #######################################################################
FROM development as build
WORKDIR /app
ARG PYTHON_TAG
ARG COMPONENT_VERSION

# Install twine for pushing the wheel to a pypi repository later
RUN pip3 install twine

COPY grpc_gateway_wrapper/ ./grpc_gateway_wrapper
COPY setup.py /app/setup.py

RUN python3 setup.py bdist_wheel --python-tag ${PYTHON_TAG} clean --all

RUN pip3 install --no-cache-dir /app/dist/grpc_gateway_wrapper*.whl

## Test ########################################################################
FROM build as test
COPY example /app/example
RUN grpc-gateway-wrapper --proto_files /app/example/*.proto \
        --metadata mm-model-id \
        --output_dir . \
        --install_deps

## release container #####################################################################
FROM development as release

# Create a release image without any of the intermediate source files

RUN true && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    true

COPY --from=build /usr/local /usr/local

# Sanity check: We can import the installed wheel
RUN grpc-gateway-wrapper --help
ENTRYPOINT ["grpc-gateway-wrapper"]
