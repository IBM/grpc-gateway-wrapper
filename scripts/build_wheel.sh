#!/bin/bash

# Version of the library that we want to tag our wheel as
release_version=${RELEASE_VERSION:-""}
GREEN='\033[0;32m'
NC='\033[0m'

function show_help
{
cat <<- EOM
Usage: scripts/build_wheels.sh -v [Library Version]
EOM
}

while (($# > 0)); do
  case "$1" in
  -h | --h | --he | --hel | --help)
    show_help
    exit 2
    ;;
  -v | --release_version)
    shift; release_version="$1";;
  *)
    echo "Unkown argument: $1"
    show_help
    exit 2
    ;;
  esac
  shift
done

if [ "$release_version" == "" ]; then
    echo "ERROR: a release version for the library must be specified."
    show_help
    exit 1
else
    echo -e "Building wheels for version: ${GREEN}${release_version}${NC}"
    sleep 2
fi
echo -e "${GREEN}Building wheel ${NC}"
RELEASE_VERSION=$release_version python3 setup.py bdist_wheel --python-tag py3 clean --all
echo -e "${GREEN}Done building wheel ${NC}"
sleep 1
