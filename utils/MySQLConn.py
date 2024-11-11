from utils import trade_common_src
from utils import trade_common_index

class MSSQL_SRC:
    def __get_connect(self):
        self.conn = trade_common_src.get_connection()
        cur = self.conn.cursor()
        if not cur:
            raise(NameError, "连接数据库失败")
        else:
            return cur

    def ExecQuery(self, sql):
        cur = self.__get_connect()
        try:
            cur.execute(sql)
            res_list = cur.fetchall()
        finally:
            self.conn.close()
        return res_list

    def ExecNonQuery(self, sql):
        cur = self.__get_connect()
        try:
            cur.execute(sql)
            self.conn.commit()
        finally:
            self.conn.close()


class MSSQL_IDX:
    def __get_connect(self):
        self.conn = trade_common_index.get_connection()
        cur = self.conn.cursor()
        if not cur:
            raise(NameError, "连接数据库失败")
        else:
            return cur

    def ExecQuery(self, sql):
        cur = self.__get_connect()
        try:
            cur.execute(sql)
            res_list = cur.fetchall()
        finally:
            self.conn.close()
        return res_list

    def ExecNonQuery(self, sql):
        cur = self.__get_connect()
        try:
            cur.execute(sql)
            self.conn.commit()
        finally:
            self.conn.close()


