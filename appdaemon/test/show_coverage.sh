#!/bin/bash
test_dir=$(realpath "$(dirname $0)")
appdaemon_dir=$(realpath "${test_dir}/../")
apps_dir=$(realpath "${appdaemon_dir}/apps/")
pushd ${appdaemon_dir} > /dev/null
coverage run --source ${apps_dir} -m pytest 
coverage report -m
coverage html 
echo ${test_dir}/htmlcov/index.html
popd > /dev/null