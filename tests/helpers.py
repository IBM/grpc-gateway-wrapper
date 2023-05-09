"""
Common test helpers
"""

# Standard
from contextlib import contextmanager
from typing import Dict, List, Union
import copy
import glob
import os
import sys
import tempfile

TEST_DATA_DIR = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        "data",
    )
)

TEST_PROTOS_DIR = os.path.join(TEST_DATA_DIR, "protos")
TEST_PROTOS = glob.glob(f"{TEST_PROTOS_DIR}/*.proto")


@contextmanager
def temp_protos(protos: Union[str, Dict[str, str]]) -> List[str]:
    """Create temporary protobuf files and yield their names"""
    with tempfile.TemporaryDirectory() as workdir:
        if isinstance(protos, str):
            protos = {"test.proto": protos}
        proto_files = []
        for proto_name, proto_content in protos.items():
            fname = os.path.join(workdir, proto_name)
            proto_files.append(fname)
            with open(fname, "w") as handle:
                handle.write(proto_content)
        yield proto_files


@contextmanager
def cli_args(*args):
    """Mock out the sys.argv set so that argparse gets the desired values"""
    real_args = copy.deepcopy(sys.argv)
    sys.argv = sys.argv[:1] + list(args)
    yield
    sys.argv = real_args
