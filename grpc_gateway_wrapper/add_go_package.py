"""
This utility function adds the "option go_package" to a proto file and resaves
it to an output location
"""

# Local
from .log import log


def add_go_package(proto_file: str):
    """
    This utility function adds the "option go_package" to a proto file and
    resaves it to an output location
    """
    log.debug("Adding go package for %s", proto_file)
    output_lines = []
    with open(proto_file, "r") as f_in:
        for raw_line in f_in:
            line = raw_line.strip()
            if "go_package" in line:
                log.debug("Removing original go_package [%s]", line.strip())
            else:
                output_lines.append(raw_line)
            if line.startswith("package"):
                package_name = line.split()[-1].rstrip(";").replace(".", "/")
                output_lines.append(
                    f'option go_package = "grpc-gateway-wrapper/{package_name}";\n'
                )
    with open(proto_file, "w") as f_out:
        f_out.write("\n".join(output_lines))
