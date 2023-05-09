"""
Tests for the utility to add metadata args to a swagger object
"""

# Standard
import json
import tempfile

# Third Party
import pytest

# Local
from grpc_gateway_wrapper.add_metadata_to_swagger import add_metadata_to_swagger

## Helpers #####################################################################

SAMPLE_SWAGGER = {
    "paths": {
        "/v1/foobar": {
            "post": {
                "parameters": [],
            },
        },
        "/v1/bazbat": {
            "post": {
                "parameters": [
                    {
                        "name": "something",
                        "schema": {
                            "default": "",
                        },
                    }
                ],
            },
        },
    },
}


@pytest.fixture
def swagger_file():
    with tempfile.NamedTemporaryFile("w", suffix="json") as swagger_file:
        json.dump(SAMPLE_SWAGGER, swagger_file)
        swagger_file.flush()
        yield swagger_file.name


## Tests #######################################################################


def test_add_metadata_to_swagger_no_defaults(swagger_file):
    """Test that the metadata arguments can be correctly added to the merged
    swagger file with no default values
    """
    metadata = ["my-metadata", "some-other-md"]
    add_metadata_to_swagger(swagger_file, metadata)
    with open(swagger_file, "r") as handle:
        swagger_content = json.load(handle)
    endpoints = swagger_content["paths"]
    assert endpoints.keys() == SAMPLE_SWAGGER["paths"].keys()
    for endpoint, endpoint_cfg in endpoints.items():
        params = endpoint_cfg["post"]["parameters"]
        orig_params = SAMPLE_SWAGGER["paths"][endpoint]["post"]["parameters"]
        assert params[: len(orig_params)] == orig_params
        new_params = params[len(orig_params) :]
        assert len(new_params) == len(metadata)
        for i, md in enumerate(metadata):
            assert new_params[i] == {
                "in": "header",
                "name": f"grpc-metadata-{md}",
                "schema": {
                    "default": "",
                    "type": "string",
                },
            }


def test_add_metadata_to_swagger_with_defaults(swagger_file):
    """Test that the metadata arguments can be correctly added to the merged
    swagger file with default values
    """
    metadata = ["my-metadata:foo", "some-other-md:bar"]
    add_metadata_to_swagger(swagger_file, metadata)
    with open(swagger_file, "r") as handle:
        swagger_content = json.load(handle)
    endpoints = swagger_content["paths"]
    assert endpoints.keys() == SAMPLE_SWAGGER["paths"].keys()
    for endpoint, endpoint_cfg in endpoints.items():
        params = endpoint_cfg["post"]["parameters"]
        orig_params = SAMPLE_SWAGGER["paths"][endpoint]["post"]["parameters"]
        assert params[: len(orig_params)] == orig_params
        new_params = params[len(orig_params) :]
        assert len(new_params) == len(metadata)
        for i, md in enumerate(metadata):
            md_name, md_dflt = md.split(":")
            assert new_params[i] == {
                "in": "header",
                "name": f"grpc-metadata-{md_name}",
                "schema": {
                    "default": md_dflt,
                    "type": "string",
                },
            }


def test_add_metadata_to_swagger_degenerate():
    """Test that the a degenerate swagger object doesn't break things"""
    with tempfile.NamedTemporaryFile("w") as swagger_file:
        swagger_file.write("{}")
        swagger_file.flush()
        metadata = ["my-metadata:foo", "some-other-md:bar"]
        add_metadata_to_swagger(swagger_file.name, metadata)
        with open(swagger_file.name, "r") as handle:
            assert json.load(handle) == {}


def test_add_metadata_to_swagger_bad_swagger():
    """Test that the a bad swagger file causes an exception"""
    with tempfile.NamedTemporaryFile("w") as swagger_file:
        swagger_file.write("{not valid json")
        swagger_file.flush()
        metadata = ["my-metadata:foo", "some-other-md:bar"]
        with pytest.raises(ValueError):
            add_metadata_to_swagger(swagger_file.name, metadata)
