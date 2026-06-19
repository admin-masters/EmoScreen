#!/bin/sh
set -eu

MYSQL_HOME="${HOME}/.local/mysql/mysql-8.0.45-macos15-arm64"

"${MYSQL_HOME}/bin/mysqladmin" --protocol=TCP -h127.0.0.1 -P3307 -uroot shutdown
