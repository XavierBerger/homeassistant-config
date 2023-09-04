#!/bin/bash
test_dir="$(dirname $0)"
appdaemon_dir="${test_dir}/../"
apps_dir="${appdaemon_dir}/apps/"
pushd ${appdaemon_dir} > /dev/null
PYTHONPATH={apps_dir} pytest-watch -- --random-order --sw -vsx $@
popd > /dev/null