#!/bin/bash
test_dir=$(realpath "$(dirname $0)")
appdaemon_dir=$(realpath "${test_dir}/../")
git_dir=$(realpath "${appdaemon_dir}/../")
apps_dir=$(realpath "${appdaemon_dir}/apps/")
pushd ${appdaemon_dir} > /dev/null
export PYTHONPATH=${apps_dir}
pytest=$(coverage run --source ${apps_dir} -m pytest | tee /dev/tty |  perl -ne '/========== (.*) ==========/ and print "$1\n"' | tail -1)
coverage=$(coverage report -m |& tee /dev/tty | perl -ne '/TOTAL.* (\S+%)/ and print "$1"')
coverage html 
echo ${test_dir}/htmlcov/index.html
pylint=$(pylint $(git ls-files '*.py' | grep -v notifier.py | grep -v hass_driver.py) --rcfile ${git_dir}/.pylintrc | tee /dev/tty | perl -ne '/at (\S+)/ and print "$1"')
anybadge -l pytest -v "${pytest}" -o -f htmlcov/pytest.svg -c "#4589CD"
anybadge -l coverage -v "${coverage}" -o -f htmlcov/coverage.svg 70=red 80=orange 90=yellow 100=green
anybadge -l pylint -v "${pylint}" -o -f htmlcov/pylint.svg 70=red 80=orange 90=yellow 100=green
popd > /dev/null