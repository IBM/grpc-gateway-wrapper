"""
Tests for generating the gateway go code from the template
"""

# Local
from grpc_gateway_wrapper.gen_gateway_go import gen_gateway_go
from grpc_gateway_wrapper.parse_proto_files import ProtoPackage, ProtoService


def test_gen_gateway_go_package_with_services():
    """Make sure that generating with a proto package that has a service defined
    correctly adds the service include and registry
    """
    svc = ProtoService(name="FooSvc")
    pkg = ProtoPackage(name="foo", services={svc.name: svc})
    pkgs = {pkg.name: pkg}
    rendered = gen_gateway_go(pkgs)
    assert f'\t {pkg.name} "grpc-gateway-wrapper/{pkg.name}"' in rendered
    assert f"{pkg.name}.Register{svc.name}HandlerFromEndpoint" in rendered


def test_gen_gateway_go_package_without_services():
    """Make sure that generating with a proto package that has no services
    defined does not add the include or registry
    """
    pkg = ProtoPackage(name="foo")
    pkgs = {pkg.name: pkg}
    rendered = gen_gateway_go(pkgs)
    assert f'\t"grpc-gateway-wrapper/{pkg.name}"' not in rendered


def test_gen_gateway_go_package_with_periods():
    """Make sure that generating with a proto package name containing periods is
    correctly handled in the rendering
    """
    svc = ProtoService(name="FooSvc")
    pkg = ProtoPackage(name="foo.bar", services={svc.name: svc})
    pkgs = {pkg.name: pkg}
    rendered = gen_gateway_go(pkgs)
    pkg_import_name = pkg.name.split(".")[-1]
    assert (
        '\t {} "grpc-gateway-wrapper/{}"'.format(
            pkg_import_name, pkg.name.replace(".", "/")
        )
        in rendered
    )
    assert (
        "{}.Register{}HandlerFromEndpoint".format(pkg_import_name, svc.name) in rendered
    )
