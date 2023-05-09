"""
Tests for our simple template compiler
"""

# Local
from grpc_gateway_wrapper.constants import GO_TEMPLATE
from grpc_gateway_wrapper.template_compiler import TemplateCompiler


def test_template_compiler_simple():
    """Make sure a simple template can be filled in"""
    template = """
    {{ key1 }}
    something {{ key2 }}
    """
    compiler = TemplateCompiler(template)
    compiled = compiler({"key1": "foo", "key2": "bar"})
    assert (
        compiled
        == """
    foo
    something bar
    """
    )


def test_template_compiler_gateway_template():
    """Make sure that the real gateway template can be compiled"""
    with open(GO_TEMPLATE, "r") as handle:
        template = handle.read()
    compiler = TemplateCompiler(template)
    compiled = compiler(
        {
            "PACKAGE_INCLUDES": "__packages__",
            "SERVICE_REGISTRATIONS": "__registrations__",
        }
    )
    assert "PACKAGE_INCLUDES" not in compiled
    assert "SERVICE_REGISTRATIONS" not in compiled
    assert "__packages__" in compiled
    assert "__registrations__" in compiled
