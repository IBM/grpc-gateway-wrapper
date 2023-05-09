#!/usr/bin/env bash
################################################################################
# MIT License
#
# Copyright (c) 2022 IBM
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

# This is a helper script that sets up a `pytest` command, for use either in or out of a develop container
source_dir=grpc_gateway_wrapper
cov_thresh=${COVERAGE_THRESHOLD:-"100.0"}

PARALLEL=${PARALLEL:-"0"}
if [ "$PARALLEL" == "1" ] &&  [[ -n $(pip freeze | grep pytest-xdist) ]];
then
  if [[ "$OSTYPE" =~ "darwin"* ]]
    then
      parallel_args="-n $(sysctl -n hw.physicalcpu) --dist=loadscope"
    else
      parallel_args="-n $(nproc) --dist=loadscope"
  fi
  echo "Running tests in parallel with ${parallel_args}"
else
  parallel_args=""
  echo "Running tests in series"
fi

coverage_args=" --cov-report term --cov-report html:htmlcov --cov=${source_dir} "
coveragerc_file="$(cd ${source_dir}/.. && pwd)/.coveragerc"
if [ -f "${coveragerc_file}" ]
then
  coverage_args="${coverage_args} --cov-config=${coveragerc_file} --cov-fail-under=${cov_thresh}"
fi
passthrough_args=()
warnings_arg="-W error"
while (($# > 0)); do
  case "$1" in
  --no-cover)
    coverage_args=""
    ;;
  --allow-warnings)
    warnings_arg="--disable-pytest-warnings"
    ;;
  *)
    passthrough_args+=("$1")
    ;;
  esac
  shift
done

if [[ "${passthrough_args[@]}" == "" ]]
then
  passthrough_args+=(tests)
fi

python3 -m pytest \
  ${coverage_args} \
  ${parallel_args} \
  ${warnings_arg} \
  --html="reports/report_${os}_${python_tag}.html" \
  --self-contained-html \
  ${passthrough_args[@]}
