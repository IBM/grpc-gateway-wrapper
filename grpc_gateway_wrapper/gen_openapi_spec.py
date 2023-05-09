"""
This module holds the gen_openapi_spec function which is responsible for
creating the OpenAPI Configuration

Ref: https://github.com/grpc-ecosystem/grpc-gateway/blob/master/docs/docs/mapping/grpc_api_configuration.md#using-an-external-configuration-file
Ref: https://github.com/grpc-ecosystem/grpc-gateway/blob/master/examples/internal/proto/examplepb/unannotated_echo_service.swagger.yaml
"""

# Standard
from typing import Dict

# Local
from .log import log
from .parse_proto_files import ProtoPackage


def gen_openapi_spec(parsed_rpcs: Dict[str, ProtoPackage]) -> dict:
    """Given the parsed dict of rpcs, generate the openapi configuration spec"""
    openapi_out = {}
    opts = openapi_out.setdefault("openapiOptions", {})
    for package in parsed_rpcs.values():
        for message in package.messages.values():
            msg_opts = {}
            if message.description:
                opts.setdefault("message", []).append(
                    {
                        "message": f"{package}.{message}",
                        "option": {
                            "json_schema": {
                                "description": message.description,
                            },
                        },
                    }
                )
            for field in message.fields.values():
                field_opts = {}
                if field.description:
                    field_opts.setdefault("option", {})[
                        "description"
                    ] = field.description
                # TODO: Support defaults by type
                if field_opts:
                    field_opts["field"] = f"{package}.{message}.{field}"
                    opts.setdefault("field", []).append(field_opts)
        for service in package.services.values():
            if service.description:
                opts.setdefault("service", []).append(
                    {
                        "service": f"{package}.{service}",
                        "option": {
                            "description": service.description,
                        },
                    }
                )
            for rpc in service.rpcs.values():
                rpc_spec = {}
                if rpc.description:
                    rpc_spec.setdefault("option", {})["description"] = rpc.description
                # TODO: Add additional options like responses
                if rpc_spec:
                    rpc_spec["method"] = f"{package}.{service}.{rpc}"
                    opts.setdefault("method", []).append(rpc_spec)
    return openapi_out
