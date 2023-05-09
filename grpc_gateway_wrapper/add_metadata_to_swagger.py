"""
This script adds a set of headers to the given swagger spec
"""

# Standard
from typing import Dict, Iterable, List, Optional
import copy
import json

# Local
from .log import log

HEADER_TEMPLATE = {
    "in": "header",
    "name": None,
    "schema": {"type": "string", "default": None},
}


def add_metadata_parameter(json_spec: Dict, name: str, default: str) -> Dict:
    """Looks for any `post`s and plops on the header corresponding to the grpc
    metadata field
    """
    path_objs = json_spec.get("paths", {})
    for path_spec in path_objs.values():
        param_list = path_spec.get("post", {}).get("parameters", [])
        header_spec = copy.deepcopy(HEADER_TEMPLATE)
        header_spec["name"] = "grpc-metadata-%s" % name
        header_spec["schema"]["default"] = default
        param_list.append(header_spec)

    return json_spec


def add_metadata_to_swagger(swagger_spec: str, metadata: Optional[Iterable[str]]):
    """Add the swagger additions to support the given list of gRPC metadata
    fields
    """
    with open(swagger_spec) as handle:
        try:
            log.debug("Loading [%s]", swagger_spec)
            js = json.load(handle)
            for metadata in metadata or []:
                name = metadata
                default_value = ""
                if ":" in metadata:
                    name, _, default_value = metadata.partition(":")

                log.debug(
                    "Adding header [%s] with default value [%s] to [%s]",
                    name,
                    default_value,
                    swagger_spec,
                )
                js = add_metadata_parameter(js, name, default_value)
        except Exception as err:
            log.error("Bad spec file [%s]: %s", swagger_spec, err)
            raise

    with open(swagger_spec, "w") as handle:
        log.debug("Writing back to [%s]", swagger_spec)
        handle.write(json.dumps(js, indent=2))
