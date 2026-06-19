#!/bin/sh
set -eu

MYSQL_HOME="${HOME}/.local/mysql/mysql-8.0.45-macos15-arm64"
MYSQL_DATA="${HOME}/.local/mysql/emoscreen-data"
MYSQL_RUN="${HOME}/.local/mysql/run"
MYSQL_LOG="${HOME}/.local/mysql/log/emoscreen.err"
MYSQL_PID="${MYSQL_RUN}/emoscreen.pid"
MYSQL_SOCKET="${MYSQL_RUN}/emoscreen.sock"

mkdir -p "${MYSQL_DATA}" "${MYSQL_RUN}" "$(dirname "${MYSQL_LOG}")"

if "${MYSQL_HOME}/bin/mysqladmin" --protocol=TCP -h127.0.0.1 -P3307 -uroot ping >/dev/null 2>&1; then
  echo "MySQL already running on 127.0.0.1:3307"
  exit 0
fi

rm -f "${MYSQL_PID}"

nohup "${MYSQL_HOME}/bin/mysqld" \
  --basedir="${MYSQL_HOME}" \
  --datadir="${MYSQL_DATA}" \
  --port=3307 \
  --socket="${MYSQL_SOCKET}" \
  --pid-file="${MYSQL_PID}" \
  --log-error="${MYSQL_LOG}" \
  --bind-address=127.0.0.1 \
  --mysqlx=0 \
  >/dev/null 2>&1 &

sleep 3
"${MYSQL_HOME}/bin/mysqladmin" --protocol=TCP -h127.0.0.1 -P3307 -uroot ping
