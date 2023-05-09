"""
Tests for the main gen_gateway script
"""

# Standard
from contextlib import contextmanager
from subprocess import CompletedProcess
from typing import List
from unittest.mock import patch
import os
import shlex
import shutil
import tempfile

# Third Party
import pytest

# Local
from grpc_gateway_wrapper.gen_gateway import main
from tests.helpers import TEST_DATA_DIR, TEST_PROTOS, cli_args, temp_protos

## Helpers #####################################################################


TEST_PROTOC_OUT = os.path.join(TEST_DATA_DIR, "protoc_output")


def fake_protoc(protoc_args: str):
    """Mock the output of protoc by copying canned output"""

    # Pull the target dir from the command. This makes NO attempt to parse the
    # correctness of the command and relies on the fact that the protos live in
    # the target output dir (which IS true for our usage).
    target_dir = protoc_args[2]
    shutil.copytree(TEST_PROTOC_OUT, target_dir, dirs_exist_ok=True)


class CmdMock:
    def __init__(self, mock_protoc=True):
        self.commands = []
        self.mock_protoc = mock_protoc

    def __call__(self, command, **_):
        command = shlex.split(command)
        self.commands.append(command)
        if self.mock_protoc and command[0] == "protoc":
            fake_protoc(command)
        return CompletedProcess(command, 0, b"", b"")


@pytest.fixture
def workdir():
    with tempfile.TemporaryDirectory() as wd:
        yield wd


@pytest.fixture
def builddir():
    with tempfile.TemporaryDirectory() as bd:
        yield bd


@pytest.fixture
def temp_cwd():
    with tempfile.TemporaryDirectory() as cwd:
        current_cwd = os.getcwd()
        os.chdir(cwd)
        try:
            yield cwd
        finally:
            os.chdir(current_cwd)


@pytest.fixture
def cmd_mock():
    cmd_mock = CmdMock()
    with patch("grpc_gateway_wrapper.gen_gateway.cmd", new=cmd_mock):
        with patch("grpc_gateway_wrapper.shell_tools.cmd", new=cmd_mock):
            yield cmd_mock


def assert_standard_cmds(commands: List[List[str]], builddir: str):
    assert len(commands) == 10
    assert all(cmd[0] == "which" for cmd in commands[:6])
    assert commands[6][0] == "protoc"
    assert commands[7] == ["go", "mod", "init", "grpc-gateway-wrapper"]
    assert commands[8] == ["go", "mod", "tidy"]
    assert commands[9] == [
        "go",
        "build",
        "-o",
        os.path.realpath(os.path.join(builddir, "app")),
    ]


## Tests #######################################################################


def test_gen_gateway_main(cmd_mock, workdir, builddir):
    """Make sure that an end-to-end run of gen_gateway works as expected. This
    test mocks out interactions with external executables, so it only tests the
    python interactions.
    """
    with cli_args(
        "--working_dir",
        workdir,
        "--output_dir",
        builddir,
        "--no_cleanup",
        "--proto_files",
        *TEST_PROTOS,
    ):
        main()
        assert os.path.isfile(
            os.path.join(workdir, "grpc-gateway-wrapper", "gateway.go")
        )
        assert os.path.isfile(os.path.join(workdir, "service.json"))
        assert os.path.isfile(os.path.join(workdir, "openapi.json"))
        assert os.path.isdir(os.path.join(builddir, "swagger"))
        assert_standard_cmds(cmd_mock.commands, builddir)


def test_gen_gateway_with_cleanup(cmd_mock, workdir, builddir):
    """Make sure that with cleanup enabled, the generated files are removed"""
    with cli_args(
        "--working_dir",
        workdir,
        "--output_dir",
        builddir,
        "--proto_files",
        *TEST_PROTOS,
    ):
        main()
        assert not os.path.isfile(
            os.path.join(workdir, "grpc-gateway-wrapper", "gateway.go")
        )
        assert not os.path.isfile(os.path.join(workdir, "service.json"))
        assert not os.path.isfile(os.path.join(workdir, "openapi.json"))
        assert os.path.isdir(os.path.join(builddir, "swagger"))
        assert_standard_cmds(cmd_mock.commands, builddir)


def test_gen_gateway_gen_temp_workdir(cmd_mock, builddir):
    """Make sure that without a workdir given, the main runs correctly"""
    with cli_args("--output_dir", builddir, "--proto_files", *TEST_PROTOS):
        main()
        assert os.path.isdir(os.path.join(builddir, "swagger"))
        assert_standard_cmds(cmd_mock.commands, builddir)


def test_gen_gateway_gen_temp_workdir(cmd_mock, workdir, builddir):
    """Make sure that with a non-existent workdir given, the dir is created"""
    nested_workdir = os.path.join(workdir, "nested")
    with cli_args(
        "--working_dir",
        nested_workdir,
        "--output_dir",
        builddir,
        "--no_cleanup",
        "--proto_files",
        *TEST_PROTOS,
    ):
        main()
        assert os.path.isfile(
            os.path.join(nested_workdir, "grpc-gateway-wrapper", "gateway.go")
        )
        assert os.path.isfile(os.path.join(nested_workdir, "service.json"))
        assert os.path.isfile(os.path.join(nested_workdir, "openapi.json"))
        assert os.path.isdir(os.path.join(builddir, "swagger"))
        assert_standard_cmds(cmd_mock.commands, builddir)


def test_gen_gateway_gen_temp_builddir(cmd_mock, temp_cwd):
    """Make sure that without a workdir or build dir given, the main runs
    correctly
    """
    with tempfile.TemporaryDirectory():
        with cli_args("--proto_files", *TEST_PROTOS):
            main()
            builddir = os.path.join(temp_cwd, "build")
            assert os.path.isdir(os.path.join(builddir, "swagger"))
            assert_standard_cmds(cmd_mock.commands, builddir)


def test_gen_gateway_bad_workdir(cmd_mock, workdir):
    """Make sure that if the workdir is a file, it raises"""
    nested_workdir = os.path.join(workdir, "nested")
    with open(nested_workdir, "w") as handle:
        handle.write("this is a file")
    with cli_args("--working_dir", nested_workdir, "--proto_files", *TEST_PROTOS):
        with pytest.raises(ValueError):
            main()


def test_gen_gateway_clean_swagger(cmd_mock, builddir):
    """Make sure that any pre-existing content in the swagger output dir is
    cleaned out before the new content is copied in
    """
    bad_swagger = os.path.join(builddir, "swagger", "some_file.json")
    os.mkdir(os.path.dirname(bad_swagger))
    with open(bad_swagger, "w") as handle:
        handle.write("{}")
    with cli_args("--output_dir", builddir, "--proto_files", *TEST_PROTOS):
        main()
        assert not os.path.isdir(bad_swagger)


def test_gen_gateway_install_go_deps(cmd_mock, builddir):
    """Make sure that the go install commands are run if requested"""
    with cli_args(
        "--install_deps", "--output_dir", builddir, "--proto_files", *TEST_PROTOS
    ):
        main()
        # The commands should be:
        #   1. verify go
        #   2. verify protoc
        #   3-6. install protoc plugins
        #   7-10. verify protoc plugins
        #   8. protoc
        #   9-14. go build setps

        assert len(cmd_mock.commands) == 14

        std_cmds = cmd_mock.commands[:2] + cmd_mock.commands[6:]
        assert_standard_cmds(std_cmds, builddir)

        install_cmds = cmd_mock.commands[2:6]
        assert all(cmd[:2] == ["go", "install"] for cmd in install_cmds)
