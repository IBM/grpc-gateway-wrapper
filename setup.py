################################################################################
# MIT License
#
# Copyright (c) 2023 IBM
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################
"""Setup to be able to build grpc_gateway_wrapper library.
"""

# Standard
import os

# Third Party
import setuptools

# Read the README to provide the long description
python_base = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(python_base, "README.md"), "r") as handle:
    long_description = handle.read()

# Read version from the env
version = os.environ.get("RELEASE_VERSION")
assert version is not None, "Must set RELEASE_VERSION"


def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


extra_files = package_files(os.path.join("grpc_gateway_wrapper", "resources"))

setuptools.setup(
    name="grpc_gateway_wrapper",
    author="IBM",
    version=version,
    license="MIT",
    description="GRPC Gateway Wrapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires="~=3.8",
    packages=setuptools.find_packages(include=("grpc_gateway_wrapper",)),
    package_data={"grpc_gateway_wrapper": extra_files},
    entry_points={
        "console_scripts": [
            "grpc-gateway-wrapper=grpc_gateway_wrapper.__main__:main",
        ]
    },
)
