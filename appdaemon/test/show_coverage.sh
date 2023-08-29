#!/bin/bash
pushd /config/appdaemon/test
coverage run --source /config/appdaemon/apps/ -m pytest 
coverage report -m
coverage html 
echo /config/appdaemon/test/htmlcov/index.html
popd