# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/8/30 10:01
# @File:        mysql_db.py
# @Software:    PyCharm
# @Description: 连接数据库的代码。
import mysql.connector
from mysql.connector import Error


class MysqlDB:

    def __init__(self, *args, **kwargs):
        self.commit = kwargs.get('commit', False)
        self.config = {
            'host': kwargs.get('host'),
            'port': kwargs.get('port'),
            'user': kwargs.get('user'),
            'password': kwargs.get('password'),
            'database': kwargs.get('database'),
            "connect_timeout": kwargs.get('connect_timeout', 10),
        }
        self.log = kwargs.get('log')
        self.conn = None
        self.cursor = None
        self.status = False

    def connect(self):
        try:
            self.conn = mysql.connector.connect(**self.config)
            self.cursor = self.conn.cursor(dictionary=True)  # 返回 dict 而不是 tuple
        except Exception as e:
            raise Exception(f"conn.is_connected() is {self.conn.is_connected()}")
        self.status = self.conn.is_connected()
        return self.conn.is_connected()

    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            result = self.cursor.fetchall()
        except Error as e:
            self._print(f"Query({query}) failed: exception({e})", "error")
            raise Exception(f"Query({query}) failed: exception({e})")
        return result

    def execute_update_many(self, query):
        try:
            self.cursor.execute(query)
            result = self.cursor.rowcount
            self.conn.commit() if self.commit else self.conn.rollback()
        except Error as e:
            q = query.replace('\n', ' ').strip()
            self._print(f"Update({q}) failed: exception({e})", "error")
            raise Exception(f"Update({q}) failed: exception({e})")
        return result

    def execute_insert_many(self, sql, data):
        if not sql:
            self._print(f"sql is None", "error")
        try:
            # 执行批量插入
            self.cursor.executemany(sql, data)
            self.conn.commit() if self.commit else self.conn.rollback()
            # self._print(f"insert data successfully | length={len(data)} | id={self.cursor.lastrowid}", "info")
            return True
        except Exception as e:
            self.conn.rollback()
            q = sql.replace('\n', '').strip()
            self._print(f"Batch insert sql({q}) failed: exception({e})", "error")
            raise Exception(f"Batch insert sql({q}) failed: exception({e})")

    def execute_insert_single(self, sql, data):
        if not sql:
            self._print(f"sql is None", "error")
        try:
            # 执行批量插入
            self.cursor.execute(sql, data)
            self.conn.commit() if self.commit else self.conn.rollback()
            return True
        except Exception as e:
            self.conn.rollback()
            q = sql.replace('\n', '').strip()
            self._print(f"Single insert sql({q}) failed: exception({e})", "error")
            raise Exception(f"Single insert sql({q}) failed: exception({e})")

    def _print(self, msg: str, level_type: str = "info"):
        if self.log:
            level_dict = {
                "info": self.log.info,
                "warn": self.log.warn,
                "error": self.log.error,
            }
            level_dict[level_type](msg)
        else:
            print(msg)

    def close_connection(self):
        self.cursor.close()
        self.conn.close()



