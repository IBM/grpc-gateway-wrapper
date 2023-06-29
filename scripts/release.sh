#!/usr/bin/env bash

# Run from the project root
cd $(dirname ${BASH_SOURCE[0]})/..

# Get the tag for this release
tag=$(echo $REF | cut -d'/' -f3-)

# Build the docker phase that will release and then test it
if docker buildx --help &>/dev/null
then
    build_command="docker buildx build --platform=linux/amd64"
else
    build_command="docker build"
fi

# First build the release phase, then build the release_test. These two phases
# don't depend on each other in docker, so buildx is "smart" and doesn't build
# release before release_test. They do depend on each other logically, though,
# so we need to build them explicitly in sequence.
build_args="
    --build-arg RELEASE_VERSION=$tag \
    --build-arg PYPI_TOKEN=${PYPI_TOKEN:-""} \
    --build-arg RELEASE_DRY_RUN=${RELEASE_DRY_RUN:-"false"}
"
$build_command . --target=release $build_args
$build_command . --target=release_test $build_args
