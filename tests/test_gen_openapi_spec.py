"""
Tests for gen_openapi_spec
"""

# Local
from grpc_gateway_wrapper.gen_openapi_spec import gen_openapi_spec
from grpc_gateway_wrapper.parse_proto_files import (
    ProtoField,
    ProtoMessage,
    ProtoPackage,
    ProtoRpc,
    ProtoService,
)


def test_gen_openapi_spec_message_field_with_comments():
    """Test that message and field comments are correctly rendered in the
    openapi spec
    """
    fld = ProtoField(name="field", type_name="string", comments=["hello", "world"])
    msg = ProtoMessage(name="Msg", fields={fld.name: fld}, comments=["the message"])
    pkg = ProtoPackage(name="pkg", messages={msg.name: msg})
    rendered = gen_openapi_spec({pkg.name: pkg})
    msgs = rendered.get("openapiOptions", {}).get("message")
    assert msgs
    msg_opts = msgs[0]
    assert msg_opts["message"] == f"{pkg}.{msg}"
    assert msg_opts["option"]["json_schema"]["description"] == msg.description

    flds = rendered.get("openapiOptions", {}).get("field")
    assert flds
    fld_opts = flds[0]
    assert fld_opts["field"] == f"{pkg}.{msg}.{fld}"
    assert fld_opts["option"]["description"] == fld.description


def test_gen_openapi_spec_message_field_without_comments():
    """Test that messages and fields without comments are correctly omitted from
    the openapi spec
    """
    fld = ProtoField(name="field", type_name="string")
    msg = ProtoMessage(name="Msg", fields={fld.name: fld})
    pkg = ProtoPackage(name="pkg", messages={msg.name: msg})
    rendered = gen_openapi_spec({pkg.name: pkg})
    msgs = rendered.get("openapiOptions", {}).get("message")
    flds = rendered.get("openapiOptions", {}).get("field")
    assert msgs is None
    assert flds is None


def test_gen_openapi_spec_service_rpc_with_comments():
    """Test that service and rpc comments are correctly rendered in the openapi
    spec
    """
    rpc = ProtoRpc(name="DoIt", comments=["hello", "world"])
    svc = ProtoService(name="Svc", rpcs={rpc.name: rpc}, comments=["the message"])
    pkg = ProtoPackage(name="pkg", services={svc.name: svc})
    rendered = gen_openapi_spec({pkg.name: pkg})

    svcs = rendered.get("openapiOptions", {}).get("service")
    assert svcs
    svc_opts = svcs[0]
    assert svc_opts["service"] == f"{pkg}.{svc}"
    assert svc_opts["option"]["description"] == svc.description

    rpcs = rendered.get("openapiOptions", {}).get("method")
    assert rpcs
    rpc_opts = rpcs[0]
    assert rpc_opts["method"] == f"{pkg}.{svc}.{rpc}"
    assert rpc_opts["option"]["description"] == rpc.description


def test_gen_openapi_spec_service_rpc_without_comments():
    """Test that service and rpc without comments are correctly omitted from the
    openapi spec
    """
    rpc = ProtoRpc(name="DoIt")
    svc = ProtoService(name="Svc", rpcs={rpc.name: rpc})
    pkg = ProtoPackage(name="pkg", services={svc.name: svc})
    rendered = gen_openapi_spec({pkg.name: pkg})
    svcs = rendered.get("openapiOptions", {}).get("service")
    rpcs = rendered.get("openapiOptions", {}).get("method")
    assert svcs is None
    assert rpcs is None
