"""
Tests for the shell tools
"""

# Standard
import sys

# Third Party
import pytest

# Local
from grpc_gateway_wrapper.shell_tools import cmd, verify_executable

## cmd #########################################################################


def test_cmd_good():
    """Make sure a known working executable can be invoked"""
    cmd(f"{sys.executable} --version")


def test_not_found_cmd():
    """Test that a command for an unknkown executable raises a FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        cmd("foobarbazbat --help")


def test_bad_cmd():
    """Test that a bad command raises a RuntimeError"""
    with pytest.raises(RuntimeError):
        cmd(f"{sys.executable} --bad-flag-that-does-not-exist")


## verify_executable ###########################################################


def test_verify_executable_known():
    """Test that verifying a valid executable works as expected"""
    verify_executable(sys.executable, "something")


def test_verify_executable_missing():
    """Test that verifying a missing executable raises a good error"""
    install_url = "foo.bar.com/install"
    with pytest.raises(
        EnvironmentError,
        match=f".*Install instructions: {install_url}",
    ):
        verify_executable("foobarbazbat", install_url)
