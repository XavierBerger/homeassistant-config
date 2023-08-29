#!/bin/bash
# Add pip install pytest-watch
PYTHONPATH=/config/appdaemon/apps/ pytest-watch -- --random-order --sw -vsx $@