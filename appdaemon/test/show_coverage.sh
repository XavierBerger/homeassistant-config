#!/bin/bash
test_dir="$(dirname $0)"
appdaemon_dir="${test_dir}/../"
apps_dir="${appdaemon_dir}/apps/"
pushd ${appdaemon_dir} > /dev/null
coverage run --source ${apps_dir} -m pytest 
coverage report -m
coverage html 
echo ${test_dir}/htmlcov/index.html
popd > /dev/null