#!/bin/bash
test_dir="$(dirname $0)"
apps_dir="$(dirname $0)/../apps/"
pushd "$(dirname $0)" > /dev/null
coverage run --source ${apps_dir} -m pytest 
coverage report -m
coverage html 
echo ${test_dir}/htmlcov/index.html
popd > /dev/null