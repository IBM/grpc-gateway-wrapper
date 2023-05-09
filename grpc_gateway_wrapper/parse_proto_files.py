"""
This utility module holds the logic for parsing a set of protobuf files into
objects that we can use to seed the go, service, and openapi generation steps.
"""

# Standard
from dataclasses import dataclass, field
from typing import Dict, Iterable, List
import copy
import re

# Local
from .log import log


def make_description(comments: List[str]) -> str:
    """Utility to consolidate multi-line comments into a single string by
    stripping comment characters and merging lines
    """
    if not comments:
        return ""

    # Right justify the comment by detecting the minimal space padding
    min_padding = min(len(line) - len(line.lstrip()) for line in comments)
    justified = [line[min_padding:] for line in comments]

    # Uncomment as either a block comment or a set of individual comment lines
    if justified[0].strip().startswith("/*"):
        uncommented = [
            re.sub(r" ?/?\*[ \*]*", "", re.sub(r" ?\*/", "", line))
            for line in justified
        ]

    else:
        uncommented = [re.sub(r"// ?", "", line) for line in justified]

    # Remove leading and trailing empty line padding, but leave intermediate
    # newline-only lines
    while uncommented[0] in ["\n", ""]:
        uncommented = uncommented[1:]
    while uncommented[-1] in ["\n", ""]:
        uncommented = uncommented[:-1]

    # Remove any explicit newlines at the ends of the lines
    uncommented = [line.rstrip("\n") for line in uncommented]
    return "\n".join(uncommented)


class _NamedProtoElement:
    def __str__(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        """Make the description from the comments"""
        return make_description(self.comments)


@dataclass
class ProtoRpc(_NamedProtoElement):
    name: str
    comments: List[str] = field(default_factory=list)


@dataclass
class ProtoService(_NamedProtoElement):
    name: str
    comments: List[str] = field(default_factory=list)
    rpcs: Dict[str, ProtoRpc] = field(default_factory=dict)


@dataclass
class ProtoField(_NamedProtoElement):
    name: str
    type_name: str
    comments: List[str] = field(default_factory=list)


@dataclass
class ProtoMessage(_NamedProtoElement):
    name: str
    comments: List[str] = field(default_factory=list)
    fields: Dict[str, ProtoField] = field(default_factory=dict)


@dataclass
class ProtoPackage(_NamedProtoElement):
    name: str
    services: Dict[str, ProtoService] = field(default_factory=dict)
    messages: Dict[str, ProtoMessage] = field(default_factory=dict)


def parse_proto_files(proto_files: Iterable[str]) -> Dict[str, ProtoPackage]:
    """Given a protobuf file, parse it into a dict of package specs"""
    packages_out = {}
    for proto_file in proto_files:
        log.debug("Parsing %s", proto_file)
        with open(proto_file, "r") as handle:
            current_package = None
            current_package_stack = []
            current_service = None
            current_message = None
            current_message_stack = []
            current_field = None
            block_comment_open = False
            message_decl_stack = []
            current_comment_lines = []
            last_line_comment = False
            last_line_field_comment = False
            for lineno, line_raw in enumerate(handle.readlines()):
                line = line_raw.strip()

                # Handle comments
                if block_comment_open or line.startswith("/*") or line.startswith("//"):

                    # If this comment extends a comment field, rebuild the field
                    # description
                    if line.startswith("//") and last_line_field_comment:
                        assert (
                            current_field is not None
                        ), f"Programming Error: Last line field comment set without current field"
                        current_field.comments.append(line)

                    # Initialize the current comment lines if needed
                    current_comment_lines = current_comment_lines or []
                    if (
                        line.startswith("/*")
                        and current_comment_lines
                        and current_comment_lines[-1].strip().startswith("//")
                    ):
                        current_comment_lines = []
                    current_comment_lines.append(line_raw)

                    # If this is the start of a block comment, open it
                    if not block_comment_open and line.startswith("/*"):
                        block_comment_open = True

                    # If not in a block comment, this is an individual comment
                    # line, but it may be connected to previous comment lines if
                    # there have been no intervening non-comment lines and the
                    # type of comment is consistent between block and //
                    if line.startswith("//") and (
                        not last_line_comment or block_comment_open
                    ):
                        current_comment_lines = [line_raw]

                    # If this is the end of a block comment, close it
                    if block_comment_open and line.endswith("*/"):
                        block_comment_open = False

                    # Mark that we're in a sequence of comment lines one way or
                    # another
                    last_line_comment = True

                # Handle non-comments
                else:
                    # By default this line does not contain a field comment
                    last_line_field_comment = False

                    # Check for a package line
                    if line.startswith("package"):
                        current_package_name = line.split()[-1].rstrip(";")
                        current_package = packages_out.setdefault(
                            current_package_name,
                            ProtoPackage(name=current_package_name),
                        )
                        assert not current_package_stack, "Can't have nested packages"
                        current_package_stack.append(current_package)
                        log.debug("Setting current_package: %s", current_package)

                    # Check for a service line
                    elif line.startswith("service"):
                        current_service_name = line.split()[1].rstrip("{")
                        assert (
                            current_package is not None
                        ), f"Found service {current_service_name} on line {lineno} with no package declaration"
                        current_service = ProtoService(
                            name=current_service_name,
                            comments=copy.copy(current_comment_lines),
                        )
                        current_package.services[current_service_name] = current_service
                        log.debug("Setting current_service: %s", current_service)

                    # Check for an rpc line
                    elif line.startswith("rpc"):
                        rpc_name = line.split()[1].split("(")[0]
                        assert (
                            current_service is not None
                        ), f"Found service {rpc_name} on line {proto_file}:{lineno} with no service declaration"
                        rpc = ProtoRpc(
                            name=rpc_name,
                            comments=copy.copy(current_comment_lines),
                        )
                        current_service.rpcs[rpc_name] = rpc
                        log.debug(
                            "Parsing rpc %s -> %s -> %s",
                            current_package,
                            current_service,
                            rpc,
                        )

                    # Check for a message begin line
                    elif line.startswith("message"):
                        message_name = line.split()[1]

                        current_message_stack.append(
                            ProtoMessage(
                                name=message_name,
                                comments=copy.copy(current_comment_lines),
                            )
                        )
                        current_message = current_message_stack[-1]
                        assert (
                            current_package is not None
                        ), f"Found message {message_name} on line {proto_file}:{lineno} with no package declaration"
                        msg_pkg_name = ".".join(
                            [current_package.name] + message_decl_stack
                        )
                        log.debug(
                            "Adding message [%s] in package [%s]",
                            message_name,
                            msg_pkg_name,
                        )
                        msg_pkg = packages_out.setdefault(
                            msg_pkg_name,
                            ProtoPackage(name=msg_pkg_name),
                        )
                        current_package_stack.append(msg_pkg)
                        current_package = current_package_stack[-1]
                        current_package.messages[message_name] = current_message
                        message_decl_stack.append(message_name)

                    # Check for a message body line
                    # TODO: Support braces on the same line!
                    elif message_decl_stack:
                        # Close the current message and pop the message stack
                        if line.endswith("}"):
                            message_decl_stack.pop()
                            current_message_stack.pop()
                            if current_message_stack:
                                current_package_stack.pop()
                                assert (
                                    current_package_stack
                                ), "Can't pop the file-level package"
                                current_package = current_package_stack[-1]
                            current_message = (
                                current_message_stack[-1]
                                if current_message_stack
                                else None
                            )

                        # The declaration of a "oneof" includes the oneof's name
                        # which is not important in this interface
                        if "oneof" in line:
                            continue

                        body_line = line.rstrip("}").strip()
                        if body_line:

                            # Handle inline comments
                            line_parts = body_line.split("//")
                            if len(line_parts) > 1:
                                last_line_field_comment = True
                                current_comment_lines.append(line_parts[1].strip())
                                body_line = line_parts[0]

                            # Parse the field
                            field_line_cleaned = re.sub(
                                r" *;", "", re.sub(r" ?= ?", " ", body_line)
                            )
                            field_line_cleaned, _ = field_line_cleaned.rsplit(
                                maxsplit=1
                            )
                            field_type, field_name = field_line_cleaned.rsplit(
                                maxsplit=1
                            )
                            assert (
                                current_message is not None
                            ), f"Got field on line {lineno} with no current message"
                            current_field = ProtoField(
                                name=field_name,
                                type_name=field_type,
                                comments=copy.copy(current_comment_lines),
                            )
                            current_message.fields[field_name] = current_field

                    # Not in a comment line
                    last_line_comment = False
                    current_comment_lines = []

    return packages_out
