"""
This module holds the gen_gateway_go function that is responsible for rendering
the go template for the gateway server based on the parsed rpcs.
"""

# Standard
from typing import Dict

# Local
from .constants import GO_TEMPLATE
from .parse_proto_files import ProtoPackage
from .template_compiler import TemplateCompiler


def gen_gateway_go(parsed_rpcs: Dict[str, ProtoPackage]) -> str:
    """Given the set of parsed RPCs, render the go server code template"""
    with open(GO_TEMPLATE, "r") as handle:
        template_content = handle.read()
        template = TemplateCompiler(template_content)

        package_includes = ""
        service_registrations = ""
        for package in parsed_rpcs.values():
            go_package = package.name.replace(".", "/")
            go_import_name = package.name.split(".")[-1]
            if package.services:
                package_includes += f"""
\t {go_import_name} "grpc-gateway-wrapper/{go_package}\""""
            for service in package.services:
                service_registrations += """
\tif err := {}.Register{}HandlerFromEndpoint(ctx, mux, *proxyEndpoint, opts); nil != err {{
\t\treturn err
\t}}
""".format(
                    go_import_name, service
                )

        return template(
            {
                "PACKAGE_INCLUDES": package_includes,
                "SERVICE_REGISTRATIONS": service_registrations,
            }
        ).replace("&quot;", '"')
