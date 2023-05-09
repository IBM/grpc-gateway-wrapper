"""
Tests for gen_service_spec
"""

# Local
from grpc_gateway_wrapper.gen_service_spec import gen_service_spec
from grpc_gateway_wrapper.parse_proto_files import ProtoPackage, ProtoRpc, ProtoService


def test_gen_service_spec():
    """Make sure that the service spec is rendered correctly for a collection of
    packages/services/rpcs
    """
    # Define the foo package with two services, each with two rpcs
    foo_a_rpc_one = ProtoRpc(name="AOne")
    foo_a_rpc_two = ProtoRpc(name="ATwo")
    foo_b_rpc_one = ProtoRpc(name="BOne")
    foo_b_rpc_two = ProtoRpc(name="BTwo")
    foo_svc_a = ProtoService(
        name="FooSvcA",
        rpcs={
            foo_a_rpc_one.name: foo_a_rpc_one,
            foo_a_rpc_two.name: foo_a_rpc_two,
        },
    )
    foo_svc_b = ProtoService(
        name="FooSvcB",
        rpcs={
            foo_b_rpc_one.name: foo_b_rpc_one,
            foo_b_rpc_two.name: foo_b_rpc_two,
        },
    )
    foo_pkg = ProtoPackage(
        name="foo",
        services={
            foo_svc_a.name: foo_svc_a,
            foo_svc_b.name: foo_svc_b,
        },
    )

    # Define the bar package with one service with a single rpc
    bar_rpc = ProtoRpc(name="DoIt")
    bar_svc = ProtoService(name="BarSvc", rpcs={bar_rpc.name: bar_rpc})
    bar_pkg = ProtoPackage(name="bar", services={bar_svc.name: bar_svc})

    # Define the top-end package mapping
    pkgs = {
        foo_pkg.name: foo_pkg,
        bar_pkg.name: bar_pkg,
    }

    # Render the service spec
    rendered = gen_service_spec(pkgs)

    # Validate the http rules
    # NOTE: For now, we are only validating that the number of rules matches the
    #   number of rpcs. We will likely make changes to this rendering soon, so
    #   the content of the rules should be validated with those changes!
    http_rules = rendered.get("http", {}).get("rules")
    assert http_rules
    assert len(http_rules) == 5
