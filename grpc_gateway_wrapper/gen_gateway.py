"""
This is the main entrypoint script go generate a woring gRPC gateway server that
can proxy between an equivalent REST API and a set of gRPC services.
"""

# Standard
from typing import Dict, Iterable
import argparse
import json
import logging
import os
import shutil
import tempfile

# Local
from .add_go_package import add_go_package
from .add_metadata_to_swagger import add_metadata_to_swagger
from .constants import SWAGGER_SERVE_ASSETS
from .gen_gateway_go import gen_gateway_go
from .gen_openapi_spec import gen_openapi_spec
from .gen_service_spec import gen_service_spec
from .log import log
from .merge_swagger import merge_swagger
from .parse_proto_files import parse_proto_files
from .shell_tools import cmd, verify_executable

## Helpers #####################################################################


def install_go_deps(gateway_version: str):
    """Install all go dependencies"""
    cmd(
        f"go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@{gateway_version}"
    )
    cmd(
        f"go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@{gateway_version}"
    )
    cmd("go install google.golang.org/protobuf/cmd/protoc-gen-go@latest")
    cmd("go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest")


def run_protoc(proto_files: Iterable[str], out_flags: Dict[str, str]):
    """Helper to run a protoc command"""
    full_proto_paths = [os.path.realpath(proto_file) for proto_file in proto_files]
    proto_parent_dirs = {
        os.path.dirname(full_proto_path) for full_proto_path in full_proto_paths
    }
    cmd(
        "protoc {} -I {}/pkg/mod {} {}".format(
            " ".join([f"-I {proto_dir}" for proto_dir in proto_parent_dirs]),
            os.environ["GOPATH"],  # NOTE: Intentionally unsafe to throw if unset
            " ".join([f"--{key}={value}" for key, value in out_flags.items()]),
            " ".join([os.path.basename(proto_file) for proto_file in proto_files]),
        ),
    )


## Main ########################################################################


def main():
    # Command line args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--proto_files",
        "-p",
        required=True,
        nargs="+",
        help="The proto file to generate from",
    )
    parser.add_argument(
        "--working_dir",
        "-w",
        help="Location for intermediate files. If none, random will be generated",
    )
    parser.add_argument(
        "--no_cleanup",
        "-c",
        action="store_true",
        default=False,
        help="Don't clean up working dir",
    )
    parser.add_argument(
        "--output_dir", "-o", default="build", help="Location for output files"
    )
    parser.add_argument(
        "--metadata",
        "-m",
        nargs="*",
        help="gRPC metadata name(s) to add to the swagger",
    )
    parser.add_argument(
        "--install_deps",
        "-d",
        action="store_true",
        default=False,
        help="Install go dependencies if they're missing",
    )
    parser.add_argument(
        "--gateway_version",
        "-g",
        default="v2.10.3",
        help="Version of the grpc-gateway tools to install if installing dependencies",
    )
    parser.add_argument(
        "--log_level",
        "-l",
        default=os.environ.get("LOG_LEVEL", "info"),
        help="Log level for informational logging",
    )
    parser.add_argument(
        "--no_json_names",
        "-j",
        action="store_true",
        default=False,
        help="Disables the use of json names (camelCase) for fields. When enabled json_names_for_fields=false is passed to the protoc call",
    )

    # Parse command line args
    args = parser.parse_args()

    # Update the log level for the shared logger
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    # Make sure all of the required tools are present
    verify_executable("go", "https://go.dev/doc/install")
    verify_executable("protoc", "https://grpc.io/docs/protoc-installation/")

    # If requested, install go deps
    if args.install_deps:
        log.info("Installing go dependencies")
        install_go_deps(args.gateway_version)

    # Verify go dependencies
    verify_executable(
        "protoc-gen-grpc-gateway",
        "github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway",
    )
    verify_executable(
        "protoc-gen-openapiv2",
        "github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2",
    )
    verify_executable("protoc-gen-go", "google.golang.org/protobuf/cmd/protoc-gen-go")
    verify_executable(
        "protoc-gen-go-grpc", "google.golang.org/grpc/cmd/protoc-gen-go-grpc"
    )

    # Set up working dir and output dir if needed
    working_dir = None
    made_working_dir = False
    if args.working_dir is not None:
        if os.path.exists(args.working_dir):
            if not os.path.isdir(args.working_dir):
                raise ValueError(f"Invalid working dir: {args.working_dir}")
        else:
            os.makedirs(args.working_dir)
            made_working_dir = True
        working_dir = args.working_dir
    else:
        working_dir = tempfile.mkdtemp(prefix="gen_gateway_")
        made_working_dir = True
    log.info("Using working dir: %s", working_dir)
    go_build_dir = os.path.join(working_dir, "grpc-gateway-wrapper")
    os.makedirs(go_build_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    # Parse the proto into its package/Service/rpc structure
    parsed_rpcs = parse_proto_files(args.proto_files)

    # Generate the service json and save it
    service_spec = gen_service_spec(parsed_rpcs)
    service_json = os.path.join(working_dir, "service.json")
    with open(service_json, "w") as handle:
        handle.write(json.dumps(service_spec, indent=2))

    # Generate the openapi config json and save it
    openapi_spec = gen_openapi_spec(parsed_rpcs)
    openapi_json = os.path.join(working_dir, "openapi.json")
    with open(openapi_json, "w") as handle:
        handle.write(json.dumps(openapi_spec, indent=2))

    # Iterate through all given proto files and perform the grpc, gateway, and
    # swagger protoc generation
    workdir_proto_files = []
    for proto_file in args.proto_files:
        log.debug("Handling proto file %s", proto_file)

        # Make a copy into the working dir so that it can be modified
        shutil.copy(proto_file, working_dir)
        workdir_proto_file = os.path.join(working_dir, os.path.basename(proto_file))
        workdir_proto_files.append(workdir_proto_file)

        # Add the go package option
        log.debug("Adding go package to %s", proto_file)
        add_go_package(workdir_proto_file)

    # Generate all protoc outputs
    log.debug("Compiling all proto files")
    gateway_opt_str = (
        f"logtostderr=true,grpc_api_configuration={service_json}:{working_dir}"
    )
    openapi_opt_str = f"openapi_configuration={openapi_json}" + (
        ",json_names_for_fields=false" if args.no_json_names else ""
    )
    run_protoc(
        workdir_proto_files,
        {
            "go_out": working_dir,
            "go-grpc_out": working_dir,
            "grpc-gateway_out": gateway_opt_str,
            "openapiv2_out": gateway_opt_str,
            "openapiv2_opt": openapi_opt_str,
        },
    )

    # Copy static swagger assets to the output dir
    swagger_asset_path = os.path.join(args.output_dir, "swagger")
    if os.path.exists(swagger_asset_path):
        shutil.rmtree(swagger_asset_path)
    shutil.copytree(SWAGGER_SERVE_ASSETS, swagger_asset_path)

    # Merge the swagger files into a unified definition
    all_swagger = [
        os.path.join(working_dir, fname)
        for fname in os.listdir(working_dir)
        if fname.endswith(".swagger.json")
    ]
    merged_swagger = os.path.join(args.output_dir, "swagger", "combined.swagger.json")
    log.debug("Merging swagger docs %s into %s", all_swagger, merged_swagger)
    merge_swagger(all_swagger, merged_swagger)

    # Add any metadata headers to the swagger definition
    log.debug("Adding metadata headers: %s", args.metadata)
    add_metadata_to_swagger(merged_swagger, args.metadata)

    # Generate the gateway.go code
    gateway_code = gen_gateway_go(parsed_rpcs)
    with open(os.path.join(go_build_dir, "gateway.go"), "w") as handle:
        handle.write(gateway_code)

    # Build the go server
    bin_out = os.path.join(os.path.realpath(args.output_dir), "app")
    log.debug("Building go server: %s", bin_out)
    cmd("go mod init grpc-gateway-wrapper", cwd=go_build_dir)
    cmd("go mod tidy", cwd=go_build_dir)
    cmd(f"go build -o {bin_out}", cwd=go_build_dir)

    # Clean up working dir
    if not args.no_cleanup:
        # Remove all files created by this script
        os.remove(os.path.join(go_build_dir, "gateway.go"))
        os.remove(os.path.join(working_dir, "service.json"))
        os.remove(os.path.join(working_dir, "openapi.json"))

        # If this script made the directory, try to remove it too
        if made_working_dir:
            shutil.rmtree(working_dir, ignore_errors=True)
