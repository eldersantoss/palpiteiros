#!/bin/sh

set -e  # Configure shell so that if one command fails, it exits

coverage erase
coverage run manage.py test
coverage report
coverage html
