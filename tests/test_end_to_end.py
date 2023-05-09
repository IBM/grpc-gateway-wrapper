"""
These tests run an end-to-end evaluation. It is more of an integration test than
a unit test, but we encapsulate it here for simplicity. It will only attempt to
run if the `go` and `protoc` executables are available.
"""

# Standard
from concurrent import futures
from contextlib import closing, contextmanager
from types import ModuleType
from typing import Optional, Tuple
import datetime
import importlib
import os
import random
import shlex
import socket
import subprocess
import sys
import tempfile
import time

# Third Party
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat
from cryptography.x509.oid import NameOID
import grpc
import pytest
import requests

# Local
from grpc_gateway_wrapper.gen_gateway import main
from grpc_gateway_wrapper.log import log
from grpc_gateway_wrapper.shell_tools import cmd, verify_executable
from tests.helpers import TEST_PROTOS, TEST_PROTOS_DIR, cli_args

## Helpers #####################################################################


def have_exe(exe_name: str) -> bool:
    try:
        verify_executable(exe_name, "")
        return True
    except RuntimeError:
        return False


# Set up the conditions for enabling these tests
HAVE_PREREQS = have_exe("protoc") and have_exe("go")


def protoc(*args):
    cmd("{} -m grpc_tools.protoc {}".format(sys.executable, " ".join(args)))


@pytest.fixture(scope="module")
def compiled_protos():
    with tempfile.TemporaryDirectory() as workdir:
        protoc(
            "-I",
            TEST_PROTOS_DIR,
            "--python_out",
            workdir,
            "--grpc_python_out",
            workdir,
            *TEST_PROTOS,
        )

        sys.path.append(workdir)
        temp_mod = ModuleType("temp_protos")
        setattr(temp_mod, "workdir", workdir)
        for fname in os.listdir(workdir):
            mod_name = fname.split(".")[0]
            mod = importlib.import_module(mod_name)
            setattr(temp_mod, mod_name, mod)
        sys.path.pop()
        yield temp_mod


@pytest.fixture(scope="module")
def built_gateway():
    with tempfile.TemporaryDirectory() as builddir:
        with cli_args(
            "--output_dir",
            builddir,
            "--install_deps",
            "--proto_files",
            *TEST_PROTOS,
        ):
            main()
            gw_app = os.path.join(builddir, "app")
            swagger_path = os.path.join(builddir, "swagger")
            yield f"{gw_app} -swagger_path {swagger_path}"


## Mock Server #################################################################


def port_open(port: int) -> bool:
    """Check whether the given port is open"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def random_port():
    """Grab a random port number"""
    return int(random.uniform(12345, 55555))


def get_available_port():
    """Look for random ports until an open one is found"""
    port = random_port()
    while not port_open(port):
        port = random_port
    return port


def generate_self_signed_tls_pair():
    """Generate a self-signed key/cert pair where the cert is its own CA"""

    # Create the private key
    log.debug("Creating private key")
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    key_pem = key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    log.debug("Private Key PEM:\n%s", key_pem.decode("utf-8"))

    # Create the certificate subject
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "foo.bar.com")])

    # Set up the list of Subject Alternate Names
    san_list = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    ]

    # Create the cert
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(
            # Our certificate will be valid for 10000 days
            datetime.datetime.utcnow()
            + datetime.timedelta(days=10000)
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(san) for san in san_list]),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(Encoding.PEM)
    return key_pem, cert_pem


class MockGreeter:
    """Server that implements a simple version of the Greeter"""

    def __init__(
        self,
        compiled_protos: ModuleType,
        enable_tls: bool = False,
        enable_mtls: Optional[str] = None,
    ):
        self.compiled_protos = compiled_protos
        self.port = get_available_port()

        # Set up the server
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        self.compiled_protos.sample_service_pb2_grpc.add_SampleServiceServicer_to_server(
            self, self._server
        )

        # Set up TLS creds if desired
        self.tls_key, self.tls_cert = (None, None)
        self.tls_key_file, self.tls_cert_file = (None, None)
        self.client_tls_key, self.client_tls_cert = (None, None)
        self.client_tls_key_file, self.client_tls_cert_file = (None, None)
        hostname_str = f"[::]:{self.port}"
        if enable_tls:
            self.tls_key, self.tls_cert = generate_self_signed_tls_pair()
            self.tls_key_file, self.tls_cert_file = self.save_tls_pair(
                "server",
                self.tls_key,
                self.tls_cert,
            )
            if enable_mtls:
                (
                    self.client_tls_key,
                    self.client_tls_cert,
                ) = generate_self_signed_tls_pair()
                (
                    self.client_tls_key_file,
                    self.client_tls_cert_file,
                ) = self.save_tls_pair(
                    "client",
                    self.client_tls_key,
                    self.client_tls_cert,
                )
                credentials = grpc.ssl_server_credentials(
                    [(self.tls_key, self.tls_cert)],
                    root_certificates=self.client_tls_cert,
                    require_client_auth=True,
                )
            else:
                credentials = grpc.ssl_server_credentials(
                    [(self.tls_key, self.tls_cert)]
                )
            self._server.add_secure_port(hostname_str, credentials)
        else:
            self._server.add_insecure_port(hostname_str)

        # Boot the server
        self._server.start()

    def close(self):
        """Stop the server at the end of a test"""
        self._server.stop(0.1).wait()

    def save_tls_pair(
        self,
        prefix: str,
        tls_key: bytes,
        tls_cert: bytes,
    ) -> Tuple[str, str]:
        """Save a tls pair using the given prefix"""
        key_file = os.path.join(self.compiled_protos.workdir, f"{prefix}.key.pem")
        cert_file = os.path.join(self.compiled_protos.workdir, f"{prefix}.cert.pem")
        with open(key_file, "wb") as handle:
            handle.write(tls_key)
        with open(cert_file, "wb") as handle:
            handle.write(tls_cert)
        return key_file, cert_file

    def Greeting(self, request, context):
        """Impl of the Greeting rpc that tacks metadata onto the response"""
        output_greeting = f"Hello [{request.name}]"
        for key, value in context.invocation_metadata():
            output_greeting += f"[{key}:{value}]"
        return self.compiled_protos.sample_messages_pb2.Response(
            greeting=output_greeting
        )


@pytest.fixture
def mock_insecure_greeter(compiled_protos):
    with closing(MockGreeter(compiled_protos)) as server:
        yield server


@pytest.fixture
def mock_tls_greeter(compiled_protos):
    with closing(MockGreeter(compiled_protos, enable_tls=True)) as server:
        yield server


@pytest.fixture
def mock_mtls_greeter(compiled_protos):
    with closing(
        MockGreeter(compiled_protos, enable_tls=True, enable_mtls=True)
    ) as server:
        yield server


@contextmanager
def start_gateway(command: str):
    """Start and terminate the gateway as a managed context"""
    try:
        proc = subprocess.Popen(shlex.split(command))
        time.sleep(1)
        yield
    finally:
        proc.terminate()
        proc.communicate()


## Tests #######################################################################


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_insecure(mock_insecure_greeter, built_gateway):
    """Test that the gateway can be built end-to-end and run against an insecure
    grpc server
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_insecure_greeter.port}"
    gw_cmd = f"{built_gateway} -serve_port {gw_port} -proxy_endpoint {proxy_endpoint}"
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"http://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_tls_serve_tls_gw_no_cert_val(mock_tls_greeter, built_gateway):
    """Test that the gateway proxy works to forward to a tls server and host a
    tls proxy with hostname verification disabled
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_tls_greeter.port}"
    client_key, client_cert = mock_tls_greeter.save_tls_pair(
        "client", *generate_self_signed_tls_pair()
    )
    gw_cmd = " ".join(
        [
            built_gateway,
            "-serve_port",
            str(gw_port),
            "-proxy_endpoint",
            proxy_endpoint,
            "-serve_cert",
            client_cert,
            "-serve_key",
            client_key,
            "-proxy_cert",
            mock_tls_greeter.tls_cert_file,
            "-proxy_no_cert_val",
        ]
    )
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"https://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
            verify=client_cert,
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_tls_serve_insecure_gw(mock_tls_greeter, built_gateway):
    """Test that the gateway proxy works to forward to a tls server and host an
    insecure proxy
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_tls_greeter.port}"
    gw_cmd = " ".join(
        [
            built_gateway,
            "-serve_port",
            str(gw_port),
            "-proxy_endpoint",
            proxy_endpoint,
            "-proxy_cert",
            mock_tls_greeter.tls_cert_file,
            "-proxy_no_cert_val",
        ]
    )
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"http://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_insecure_serve_tls_gw(mock_insecure_greeter, built_gateway):
    """Test that the gateway proxy works to forward to an insecure server and
    host a tls proxy
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_insecure_greeter.port}"
    client_key, client_cert = mock_insecure_greeter.save_tls_pair(
        "client", *generate_self_signed_tls_pair()
    )
    gw_cmd = " ".join(
        [
            built_gateway,
            "-serve_port",
            str(gw_port),
            "-proxy_endpoint",
            proxy_endpoint,
            "-serve_cert",
            client_cert,
            "-serve_key",
            client_key,
        ]
    )
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"https://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
            verify=client_cert,
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_tls_serve_tls_gw_with_cert_val(mock_tls_greeter, built_gateway):
    """Test that the gateway proxy works to forward to a tls server and host a
    tls proxy with hostname verification enabled
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_tls_greeter.port}"
    client_key, client_cert = mock_tls_greeter.save_tls_pair(
        "client", *generate_self_signed_tls_pair()
    )
    gw_cmd = " ".join(
        [
            built_gateway,
            "-serve_port",
            str(gw_port),
            "-proxy_endpoint",
            proxy_endpoint,
            "-serve_cert",
            client_cert,
            "-serve_key",
            client_key,
            "-proxy_cert",
            mock_tls_greeter.tls_cert_file,
            "-proxy_cert_hname",
            "localhost",
        ]
    )
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"https://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
            verify=client_cert,
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_mtls_both(mock_mtls_greeter, built_gateway):
    """Test that the gateway proxy works to forward to an mtls server and host
    an mtls proxy
    """
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_mtls_greeter.port}"
    gw_cmd = " ".join(
        [
            built_gateway,
            "-serve_port",
            str(gw_port),
            "-proxy_endpoint",
            proxy_endpoint,
            "-serve_cert",
            mock_mtls_greeter.client_tls_cert_file,
            "-serve_key",
            mock_mtls_greeter.client_tls_key_file,
            "-proxy_mtls_cert",
            mock_mtls_greeter.client_tls_cert_file,
            "-proxy_mtls_key",
            mock_mtls_greeter.client_tls_key_file,
            "-proxy_cert",
            mock_mtls_greeter.tls_cert_file,
            "-proxy_cert_hname",
            "localhost",
            "-mtls_client_ca",
            mock_mtls_greeter.client_tls_cert_file,
        ]
    )
    with start_gateway(gw_cmd):
        resp = requests.post(
            f"https://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
            cert=(
                mock_mtls_greeter.client_tls_cert_file,
                mock_mtls_greeter.client_tls_key_file,
            ),
            verify=mock_mtls_greeter.client_tls_cert_file,
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting


@pytest.mark.skipif(not HAVE_PREREQS, reason="Missing go or protoc")
def test_end_to_end_metadata_proxy(mock_insecure_greeter, built_gateway):
    """Test that headers can proxy to grpc metadata"""
    # Start up the gateway pointed at the running greeter
    gw_port = get_available_port()
    proxy_endpoint = f"localhost:{mock_insecure_greeter.port}"
    gw_cmd = f"{built_gateway} -serve_port {gw_port} -proxy_endpoint {proxy_endpoint}"
    with start_gateway(gw_cmd):
        md_name = "custom-metadata"
        md_val = "my val"
        header_name = f"grpc-metadata-{md_name}"
        resp = requests.post(
            f"http://localhost:{gw_port}/v1/sample/SampleService/Greeting",
            json={"name": "Gabe"},
            headers={header_name: md_val},
        )
        resp.raise_for_status()
        greeting = resp.json()["greeting"]
        assert "Hello [Gabe]" in greeting
        assert f"[{md_name}:{md_val}]" in greeting
