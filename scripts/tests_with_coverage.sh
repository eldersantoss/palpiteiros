#!/bin/bash

set -e  # Configure shell so that if one command fails, it exits

coverage run manage.py test
coverage html
