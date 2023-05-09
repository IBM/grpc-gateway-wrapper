"""
This module holds the gen_service_spec function which is responsible for
creating the Google API service specification

Ref: https://cloud.google.com/endpoints/docs/grpc-service-config/reference/rpc/google.api
"""

# Standard
from typing import Dict

# Local
from .log import log
from .parse_proto_files import ProtoPackage


def gen_service_spec(parsed_rpcs: Dict[str, ProtoPackage]) -> dict:
    """Given the parsed dict of rpcs, generate the service spec dict for the
    gateway
    """
    service_out = {
        "type": "google.api.Service",
        "config_version": 3,
        "http": {"rules": []},
    }
    rules = service_out["http"]["rules"]
    for package in parsed_rpcs.values():
        for service in package.services.values():
            for rpc in service.rpcs.values():
                log.debug("Adding rpc %s -> %s -> %s", package, service, rpc)
                rules.append(
                    {
                        "selector": f"{package}.{service}.{rpc}",
                        "post": f"/v1/{package}/{service}/{rpc}",
                        "body": "*",
                    }
                )
    return service_out
