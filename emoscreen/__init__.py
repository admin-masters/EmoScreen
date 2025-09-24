# emoscreen/__init__.py
try:
    import pymysql  # noqa
    pymysql.install_as_MySQLdb()
except Exception:
    pass
