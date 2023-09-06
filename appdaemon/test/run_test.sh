#!/bin/bash
test_dir=$(realpath "$(dirname $0)")
appdaemon_dir=$(realpath "${test_dir}/../")
apps_dir=$(realpath "${appdaemon_dir}/apps/")
pushd ${appdaemon_dir} > /dev/null
PYTHONPATH="${apps_dir}" pytest-watch -- --random-order --sw -vsx $@
popd > /dev/null