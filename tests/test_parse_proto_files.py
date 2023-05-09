"""
Tests for the functionality in parse_proto_files
"""

# Local
from grpc_gateway_wrapper.parse_proto_files import make_description, parse_proto_files
from tests.helpers import temp_protos

## make_description ############################################################


def test_make_description_empty():
    """Make sure an empty comment list is handled correctly"""
    assert make_description([]) == ""
    assert make_description(None) == ""


def test_make_description_block_comment():
    """Make sure that a block comment with indentation is presented correctly"""
    full_comment = """
        /**
         * This is some
         * multi-line block comment
         */""".strip(
        "\n"
    )
    assert (
        make_description(full_comment.split("\n"))
        == "This is some\nmulti-line block comment"
    )


def test_make_description_single_line_block_comment():
    """Make sure that a single-line block comment is parsed correctly"""
    full_comment = "/** This is some */"
    assert make_description(full_comment.split("\n")) == "This is some"


def test_make_description_multi_line_comment_group():
    """Make sure that a multi-line group of // comments are parsed correctly"""
    full_comment = """
        // This is some
        // multi-line block comment""".strip(
        "\n"
    )
    assert (
        make_description(full_comment.split("\n"))
        == "This is some\nmulti-line block comment"
    )


## parse_proto_files ###########################################################


def test_parse_proto_files_single_service():
    """Test an example of a protobuf file with a single service"""
    pkg_name = "tests"
    msg_comment = "The message"
    msg_name = "TheOne"
    field_type = "string"
    field_name = "the_field"
    field_comment = "A comment about the field"
    svc_comment = "The service"
    svc_name = "TheService"
    rpc_name = "TheDoit"
    rpc_comments = ["The main endpoint", "seriously, it's important"]
    with temp_protos(
        f"""
        syntax = "proto3";
        package = {pkg_name};

        /** {msg_comment} */
        message {msg_name} {{
            {field_type} {field_name} = 1; // {field_comment}
        }}

        /**
         * {svc_comment}
         */
        service {svc_name} {{
            /**
             * {rpc_comments[0]}
             * {rpc_comments[1]}
             */
            rpc {rpc_name}({msg_name}) returns ({msg_name}) {{}}
        }}
        """
    ) as proto_files:
        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        assert list(parsed_pkgs.keys()) == [pkg_name]

        # Check the package
        test_pkg = parsed_pkgs[pkg_name]
        assert test_pkg.name == pkg_name
        assert list(test_pkg.messages.keys()) == [msg_name]
        assert list(test_pkg.services.keys()) == [svc_name]

        # Check the message
        msg = test_pkg.messages[msg_name]
        assert msg.name == msg_name
        assert msg.description == msg_comment
        assert list(msg.fields.keys()) == [field_name]

        # Check the field
        fld = msg.fields[field_name]
        assert fld.name == field_name
        assert fld.type_name == field_type
        assert fld.description == field_comment

        # Check the service
        svc = test_pkg.services[svc_name]
        assert svc.name == svc_name
        assert svc.description == svc_comment
        assert list(svc.rpcs.keys()) == [rpc_name]

        # Check the rpc
        rpc = svc.rpcs[rpc_name]
        assert rpc.name == rpc_name
        assert rpc.description == "\n".join(rpc_comments)

        # For coverage ;)
        assert str(rpc) == rpc.name


def test_parse_proto_files_consecutive_comments():
    """Test handling of consecutive comments"""
    pkg_name = "tests"
    msg_comment = "The message"
    msg_name = "TheOne"
    with temp_protos(
        f"""
        syntax = "proto3";
        package = {pkg_name};

        // Some global comment
        /** {msg_comment} */
        message {msg_name} {{
            string foo = 1;
        }}
        """
    ) as proto_files:
        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        assert list(parsed_pkgs.keys()) == [pkg_name]

        # Check the package
        test_pkg = parsed_pkgs[pkg_name]
        assert test_pkg.name == pkg_name
        assert list(test_pkg.messages.keys()) == [msg_name]

        # Make sure the message comment does not include the global comment
        assert test_pkg.messages[msg_name].description == msg_comment


def test_parse_proto_files_msgs_separate_file():
    """Make sure that a package can be split over multiple files"""
    pkg_name = "tests"
    msg_comment = "The message"
    msg_name = "TheOne"
    field_type = "string"
    field_name = "the_field"
    field_comment = "A comment about the field"
    svc_comment = "The service"
    svc_name = "TheService"
    rpc_name = "TheDoit"
    rpc_comments = ["The main endpoint", "seriously, it's important"]
    with temp_protos(
        {
            "message.proto": f"""
            syntax = "proto3";
            package = {pkg_name};

            /** {msg_comment} */
            message {msg_name} {{
                {field_type} {field_name} = 1; // {field_comment}
            }}
            """,
            "service.proto": f"""
            syntax = "proto3";
            package = {pkg_name};
            import "message.proto";

            /**
            * {svc_comment}
            */
            service {svc_name} {{
                /**
                * {rpc_comments[0]}
                * {rpc_comments[1]}
                */
                rpc {rpc_name}({msg_name}) returns ({msg_name}) {{}}
            }}
            """,
        }
    ) as proto_files:
        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        assert list(parsed_pkgs.keys()) == [pkg_name]

        # Check the package
        test_pkg = parsed_pkgs[pkg_name]
        assert test_pkg.name == pkg_name
        assert list(test_pkg.messages.keys()) == [msg_name]
        assert list(test_pkg.services.keys()) == [svc_name]

        # Check the message
        msg = test_pkg.messages[msg_name]
        assert msg.name == msg_name
        assert msg.description == msg_comment
        assert list(msg.fields.keys()) == [field_name]

        # Check the field
        fld = msg.fields[field_name]
        assert fld.name == field_name
        assert fld.type_name == field_type
        assert fld.description == field_comment

        # Check the service
        svc = test_pkg.services[svc_name]
        assert svc.name == svc_name
        assert svc.description == svc_comment
        assert list(svc.rpcs.keys()) == [rpc_name]

        # Check the rpc
        rpc = svc.rpcs[rpc_name]
        assert rpc.name == rpc_name
        assert rpc.description == "\n".join(rpc_comments)

        # For coverage ;)
        assert str(rpc) == rpc.name


def test_parse_proto_files_non_primitive_fields():
    """Make sure field parsing works for various flavors of complex fields"""
    repeated_field_name = "rep_fld"
    repeated_field_type = "repeated string"
    repeated_field_comment = "A repeated field"
    map_field_name = "map_fld"
    map_field_type = "map<string, string>"
    map_field_comment = "A map field"
    obj_field_name = "obj_fld"
    obj_field_type = "Timestamp"
    obj_field_comment = "An object field"
    with temp_protos(
        f"""
        syntax = "proto3";
        package = tests;
        message TheOne {{
            {repeated_field_type} {repeated_field_name}=1;// {repeated_field_comment}
            {map_field_type} {map_field_name}=2;          // {map_field_comment}
            {obj_field_type} {obj_field_name}=3;          // {obj_field_comment}
        }}
        """
    ) as proto_files:

        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        msg = list(list(parsed_pkgs.values())[0].messages.values())[0]
        assert set(msg.fields.keys()) == {
            repeated_field_name,
            map_field_name,
            obj_field_name,
        }

        repeated_field = msg.fields[repeated_field_name]
        assert repeated_field.type_name == repeated_field_type
        assert repeated_field.description == repeated_field_comment

        map_field = msg.fields[map_field_name]
        assert map_field.type_name == map_field_type
        assert map_field.description == map_field_comment

        obj_field = msg.fields[obj_field_name]
        assert obj_field.type_name == obj_field_type
        assert obj_field.description == obj_field_comment


def test_parse_proto_files_multiline_inline_field():
    """Test support for field comments that begin as inline and extend to empty
    lines below the field declaration
    """
    field_comments = ["line one", "line two"]
    with temp_protos(
        f"""
        syntax = "proto3";
        package = tests;
        message TheOne {{
            string foo = 1; // {field_comments[0]}
                            // {field_comments[1]}
        }}

        // Some other comment
        """
    ) as proto_files:

        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        field = list(
            list(list(parsed_pkgs.values())[0].messages.values())[0].fields.values()
        )[0]
        assert field.description == "\n".join(field_comments)


def test_parse_proto_files_nested_messages():
    """Test an example of a protobuf file with nested messages"""
    pkg_name = "tests"
    msg_name = "TheOne"
    nested_msg_name = "NestedOne"
    nested_field_type = "string"
    nested_field_name = "the_nested_field"
    field_name = "the_field"
    nested_pkg_name = ".".join([pkg_name, msg_name])
    with temp_protos(
        f"""
        syntax = "proto3";
        package = {pkg_name};

        message {msg_name} {{
            message {nested_msg_name} {{
                {nested_field_type} {nested_field_name} = 1;
            }}
            {nested_msg_name} {field_name} = 1;
        }}
        """
    ) as proto_files:
        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        assert set(parsed_pkgs.keys()) == {pkg_name, nested_pkg_name}

        # Check the packages
        test_pkg = parsed_pkgs[pkg_name]
        nested_msg_pkg = parsed_pkgs[nested_pkg_name]
        assert test_pkg.name == pkg_name
        assert set(test_pkg.messages.keys()) == {msg_name}
        assert nested_msg_pkg.name == nested_pkg_name
        assert set(nested_msg_pkg.messages.keys()) == {nested_msg_name}

        # Check the messages
        msg = test_pkg.messages[msg_name]
        nested_msg = nested_msg_pkg.messages[nested_msg_name]
        assert msg.name == msg_name
        assert nested_msg.name == nested_msg_name
        assert set(msg.fields.keys()) == {field_name}
        assert set(nested_msg.fields.keys()) == {nested_field_name}

        # Check the fields
        fld = msg.fields[field_name]
        nested_fld = nested_msg.fields[nested_field_name]
        assert fld.name == field_name
        assert nested_fld.name == nested_field_name
        assert fld.type_name == nested_msg_name
        assert nested_fld.type_name == nested_field_type


def test_parse_proto_files_oneofs():
    """Test an example of a protobuf file with a oneof"""
    pkg_name = "tests"
    msg_name = "TheOne"
    field1_name = "str_filed"
    field1_type = "string"
    field2_name = "int_field"
    field2_type = "int32"
    oneof_name = "one_of_these"
    with temp_protos(
        f"""
        syntax = "proto3";
        package = {pkg_name};

        message {msg_name} {{
            oneof {oneof_name} {{
                {field1_type} {field1_name} = 1;
                {field2_type} {field2_name} = 2;
            }}
        }}
        """
    ) as proto_files:
        # Parse it
        parsed_pkgs = parse_proto_files(proto_files)
        assert set(parsed_pkgs.keys()) == {pkg_name}

        # Check the package
        test_pkg = parsed_pkgs[pkg_name]
        assert test_pkg.name == pkg_name
        assert set(test_pkg.messages.keys()) == {msg_name}

        # Check the message (make sure oneof name is not in there)
        msg = test_pkg.messages[msg_name]
        assert msg.name == msg_name
        assert set(msg.fields.keys()) == {field1_name, field2_name}
