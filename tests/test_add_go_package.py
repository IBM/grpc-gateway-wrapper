"""
Tests for add_go_package
"""

# Local
from grpc_gateway_wrapper.add_go_package import add_go_package
from tests.helpers import temp_protos


def test_add_go_package_adds_package():
    """Make sure the go package is added correctly"""
    with temp_protos(
        """
        syntax = "proto3";
        package = tests;
        """
    ) as proto_files:
        add_go_package(proto_files[0])
        with open(proto_files[0], "r") as handle:
            rewritten_lines = [
                line.strip() for line in handle.readlines() if line.strip()
            ]
        assert 'option go_package = "grpc-gateway-wrapper/tests";' in rewritten_lines


def test_add_go_package_removes_old_package():
    """Make sure the old go package is removed before the new package is added"""
    with temp_protos(
        """
        syntax = "proto3";
        package = tests;
        option go_package = "something/else";
        """
    ) as proto_files:
        add_go_package(proto_files[0])
        with open(proto_files[0], "r") as handle:
            rewritten_lines = [
                line.strip() for line in handle.readlines() if line.strip()
            ]
        assert 'option go_package = "grpc-gateway-wrapper/tests";' in rewritten_lines
        assert 'option go_package = "something/else";' not in rewritten_lines
