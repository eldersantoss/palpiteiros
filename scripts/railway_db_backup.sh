#!/bin/bash

set -e  # Configure shell so that if one command fails, it exits

railway link $RAILWAY_PROJECT_ID
railway run pg_dump -U $DB_USER -h $DB_HOST -p $DB_PORT -n public -F t $DB_NAME > db/backup/latest.tar
