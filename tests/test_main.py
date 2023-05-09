"""
Test coverage for __main__
"""

# Local
from grpc_gateway_wrapper import __main__ as main_mod
from grpc_gateway_wrapper.gen_gateway import main


def test_main_help():
    """For the sake of coverage, make sure the main module has the right main
    function
    """
    assert main_mod.main is main
