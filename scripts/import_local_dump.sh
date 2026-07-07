#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /absolute/path/to/emoscreenlocal.sql" >&2
  exit 1
fi

MYSQL_HOME="${HOME}/.local/mysql/mysql-8.0.45-macos15-arm64"
DUMP_PATH="$1"

"${MYSQL_HOME}/bin/mysql" --protocol=TCP -h127.0.0.1 -P3307 -uroot < "${DUMP_PATH}"
