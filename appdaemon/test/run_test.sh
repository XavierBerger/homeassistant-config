#!/bin/bash
test_dir="$(dirname $0)"
apps_dir="${test_dir}/../apps/"
pushd ${test_dir} > /dev/null
PYTHONPATH={apps_dir} pytest-watch -- --random-order --sw -vsx $@
popd > /dev/null