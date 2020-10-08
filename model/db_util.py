# -*- coding: utf-8 -*-
import pymysql
from model.project import *
import datetime


class DBTool(object):

    def __init__(self, host, port, user, password, db, charset="utf8"):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._db = db
        self._charset = charset
        # 数据库连接对象
        self._conn = None
        self._cur = None

    def __del__(self):
        self.close()

    def connect(self):
        if self._conn is None:
            self._conn = pymysql.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                passwd=self._password,
                db=self._db,
                charset=self._charset,
                autocommit=1
            )
            self._cur = self._conn.cursor()

    def close(self):
        if self._conn is not None:
            self._cur.close()
            self._conn.close()
            self._conn = None

    def is_alive(self):
        if self._conn is None:
            return False
        else:
            try:
                self._conn.ping()
                return True
            except Exception:
                self._conn = None
                return False

    def import_rconfigs(self):
        sql = "SELECT * FROM radar_config"
        self._cur.execute(sql)
        rows = self._cur.fetchall()
        rcs = {}
        for row in rows:
            rc = RConfig()
            desc = row[0]
            angle_h = row[1]
            angle_v = row[2]
            pos_x = row[3]
            pos_y = row[4]
            room_x_len = row[5]
            room_y_len = row[6]
            remarks = row[7]
            product_id = row[8]
            status = row[9]
            rc.r_h_agl = angle_h
            rc.r_v_agl = angle_v
            rc.bk_w = room_x_len
            rc.bk_h = room_y_len
            rc.r_x_offset = pos_x
            rc.r_y_offset = pos_y
            rc.remarks = remarks
            rcs[desc] = rc
        return rcs

    def export_rconfigs(self, rconfigs):
        sql = "DELETE FROM radar_config;"
        self._cur.execute(sql)
        for desc, rc in rconfigs.items():
            sql = "INSERT INTO radar_config (radar_id, angle_h, angle_v, pos_x, pos_y, room_x_len, room_y_len, " \
                  "remarks, status) VALUES ('%s', '%f', '%f', '%f', '%f', '%f', '%f', '%s', '%d');" % \
                  (desc, rc.r_h_agl, rc.r_v_agl, rc.r_x_offset, rc.r_y_offset, rc.bk_w, rc.bk_h, rc.remarks, 1)
            self._cur.execute(sql)

    def update_radar_config(self, desc, rconfig):
        sql = "UPDATE radar_config SET angle_h='%f', angle_v='%f', pos_x='%f', pos_y='%f', room_x_len='%f', " \
              "room_y_len='%f', remarks='%s' WHERE radar_id='%s';" % \
              (rconfig.r_h_agl, rconfig.r_v_agl, rconfig.r_x_offset, rconfig.r_y_offset, rconfig.bk_w, rconfig.bk_h,
               rconfig.remarks, desc)
        self._cur.execute(sql)

    def update_radar_status(self, desc, status, product_id=""):
        sql = "UPDATE radar_config SET status='%d', product_id='%s' WHERE radar_id='%s';" % (status, product_id, desc)
        self._cur.execute(sql)

    def reset_all_radar_status(self, status=1):
        sql = "UPDATE radar_config SET status='%d';" % status
        self._cur.execute(sql)

    def insert_rconfig(self, desc, rc):
        sql = "INSERT INTO radar_config (radar_id, angle_h, angle_v, pos_x, pos_y, room_x_len, room_y_len, " \
              "remarks, status) VALUES ('%s', '%f', '%f', '%f', '%f', '%f', '%f', '%s', '%d');" % \
              (desc, rc.r_h_agl, rc.r_v_agl, rc.r_x_offset, rc.r_y_offset, rc.bk_w, rc.bk_h, rc.remarks, 1)
        try:
            self._cur.execute(sql)
        except Exception as e:
            print(e)

    def delete_rconfig(self, desc):
        sql = "DELETE FROM radar_config WHERE radar_id='%s';" % desc
        self._cur.execute(sql)

    def insert_targets(self, desc, targets):
        today = datetime.date.today()
        print(today.strftime('%y%m%d'))
        for t in targets:
            sql = "INSERT INTO radar_targets (target_id, radar_id, x, y, z, detect_time) VALUES ('%d', '%s', '%f', " \
                  "'%f', '%f', now());" % (t.tid, desc, t.x, t.y, t.z)
            self._cur.execute(sql)


if __name__ == "__main__":
    ex = DBTool("192.168.1.87", 3306, "vave_test_user", "vave_muniu", "vave_test")
    ex.connect()
    ex.close()




