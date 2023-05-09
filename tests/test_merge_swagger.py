"""
Tests for the functionality in the merge_swagger utility
"""

# Standard
from contextlib import contextmanager
from typing import List
import json
import os
import tempfile

# Third Party
import pytest

# Local
from grpc_gateway_wrapper.merge_swagger import merge_swagger

## Helpers #####################################################################


@contextmanager
def temp_json_files(*dicts: List[dict]) -> List[str]:
    """Dump the given dicts to json files"""
    with tempfile.TemporaryDirectory() as workdir:
        fnames = []
        for i, dct in enumerate(dicts):
            fname = os.path.join(workdir, f"file{i}.json")
            with open(fname, "w") as handle:
                json.dump(dct, handle)
            fnames.append(fname)
        yield fnames


## Tests #######################################################################


def test_merge_swagger_nested_dicts():
    """Make sure nested dicts merge cleanly"""
    with temp_json_files(
        {"foo": {"bar": [1, 2, 3], "baz": 42}}, {"foo": {"baz": 3.14}}, {"bop": "other"}
    ) as fnames:
        workdir = os.path.dirname(fnames[0])
        destination = os.path.join(workdir, "merged.json")
        merge_swagger(fnames, destination)
        with open(destination, "r") as handle:
            merged = json.load(handle)
        assert merged == {
            "foo": {
                "bar": [1, 2, 3],
                "baz": 3.14,
            },
            "bop": "other",
        }


def test_merge_swagger_bad_spec_file():
    """Test that bad files raise appropriate errors"""
    with tempfile.NamedTemporaryFile("w") as handle:
        handle.write("{Not valid json")
        handle.flush()
        with pytest.raises(ValueError):
            merge_swagger([handle.name], "not going to be used")
