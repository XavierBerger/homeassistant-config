#!/bin/bash
test_dir=$(realpath "$(dirname $0)")
appdaemon_dir=$(realpath "${test_dir}/../")
git_dir=$(realpath "${appdaemon_dir}/../")
apps_dir=$(realpath "${appdaemon_dir}/apps/")
pushd ${appdaemon_dir} > /dev/null
export PYTHONPATH=${apps_dir}
value=$(coverage run --source ${apps_dir} -m pytest | tee /dev/tty |  perl -ne '/\[(.*)\]/ and print "$1\n"' | tail -1)
anybadge -l "pytest success" -v ${value} -o -f ../images/pytest.svg 70=red 80=orange 90=yellow 100=green
value=$(coverage report -m |& tee /dev/tty | perl -ne '/TOTAL.* (\S+%)/ and print "$1"')
anybadge -l coverage -v ${value} -o -f ../images/coverage.svg 70=red 80=orange 90=yellow 100=green
coverage html 
echo ${test_dir}/htmlcov/index.html
value=$(pylint $(git ls-files '*.py' | grep -v notifier.py | grep -v hass_driver.py) --rcfile ${git_dir}/.pylintrc | tee /dev/tty | perl -ne '/at (\S+)/ and print "$1"')
anybadge -l pylint -v "${value}" -o -f ../images/pylint.svg 70=red 80=orange 90=yellow 100=green
popd > /dev/null