# -*- coding: utf-8 -*-
'''
Copyright 2020, Ainstein Inc. All Rights Reserved


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Contact: hi@ainstein.ai
 '''
import socketserver
from PyQt5 import QtCore
from queue import Queue
from xmodem import XMODEM
import os
import math
import logging
from worker.msg.msg_485 import *
from worker.worker_base import *
from worker.msg.msg_detail import *
import socket
import datetime


class WifiTCPHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.is_run = True
        self.cfg_cmds = None
        self.firm_path = None
        self.sbl_path = None
        self.query_desc = None
        self.timeout = 0.01
        self.ip_port = ""
        self.radar_timeout = WorkerWifi.radar_timeout
        self.comm_timeout = WorkerWifi.comm_timeout
        # 心跳检测间隔
        self.ds = DeviceState()
        #
        self.alive_time = 0
        #
        self.is_radar = False
        super(WifiTCPHandler, self).__init__(request, client_address, server)

    def send(self, data):
        # print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
        # print("send:", end="")
        # for b in data:
        #     print("%02x " % b, end="")
        # print("")
        self.request.sendall(data)

    def recv(self, count):
        data = None
        try:
            data = self.request.recv(count)
        except socket.timeout:
            pass
        if data is not None and len(data) > 0:
            # 收到数据即认为雷达存活
            self.alive_time = time.time()
            # print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
            # print("recv:", end="")
            # for b in data:
            #     print("%02x " % b, end="")
            # print("")
        return data

    def end(self):
        self.is_run = False

    def handle(self):
        print("Radar connected via WiFi", self.client_address)
        # 将新的TCP连接记录到字典
        # self.ip_port = self.client_address[0] + ":" + str(self.client_address[1])
        self.ip_port = self.client_address[0]
        if self.ip_port in WorkerWifi.dict_clients.keys():
            WorkerWifi.dict_clients[self.ip_port].end()
            time.sleep(2)
        WorkerWifi.dict_clients[self.ip_port] = self
        # 设置超时时间
        self.request.settimeout(self.timeout)
        #
        self.alive_time = time.time()
        # 主循环
        while self.is_run:
            if time.time() - self.alive_time >= 40:
                print("not alive")
                break
            time.sleep(0.005)
            # 心跳检测（获取版本号）
            if self.ds.need_get_version():
                self.send(bytes("getVersion\n", "utf-8"))
                ret, msg_detail = self.get_msg485(CMD_485_VERSION, timeout=self.radar_timeout)
                if ret:
                    WorkerWifi.queue_msg.put((self.ip_port, msg_detail))
                    self.ds.set_radar()
            # 下发CFG
            try:
                if self.cfg_cmds is not None:
                    self.send_cfg_cmds()
                    self.cfg_cmds = None
                    self.ds.reset()
                    time.sleep(5)
            except Exception as e:
                WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_CFG, str(e)))
                break
            # update firmware
            try:
                if self.firm_path is not None:
                    self.update_firmware()
                    self.firm_path = None
                    self.ds.reset()
            except Exception as e:
                WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_FIRM, str(e)))
                break
            # update sbl
            try:
                if self.sbl_path is not None:
                    self.update_sbl()
                    self.sbl_path = None
                    self.ds.reset()
            except Exception as e:
                WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_SBL, str(e)))
                break
            # 接收目标数据
            if self.ds.is_radar() and self.ds.need_get_target():
                try:
                    if WorkerWifi.debug_target:
                        self.send(bytes("getDebugTarget\n", "utf-8"))
                        ret, msg_detail = self.get_msg485(CMD_485_DEBUG_TARGET, timeout=self.comm_timeout)
                    elif WorkerWifi.detail_target:
                        self.send(bytes("getDetailTarget\n", "utf-8"))
                        ret, msg_detail = self.get_msg485(CMD_485_DETAIL_TARGET, timeout=self.comm_timeout)
                    else:
                        self.send(bytes("getTarget\n", "utf-8"))
                        ret, msg_detail = self.get_msg485(CMD_485_TARGET, timeout=self.comm_timeout)
                    if ret:
                        WorkerWifi.queue_msg.put((self.ip_port, msg_detail))
                except Exception as e:
                    print(e)
                    break
            # 查询
            if self.query_desc is not None:
                if self.ds.is_radar():
                    self.send(bytes("getConf\n", "utf-8"))
                    ret, msg_detail = self.get_msg485(CMD_485_CONFIG, timeout=self.comm_timeout)
                    if ret:
                        WorkerWifi.queue_msg.put((self.ip_port, msg_detail))
                    self.send(bytes("getWorkParam\n", "utf-8"))
                    ret, msg_detail = self.get_msg485(CMD_485_PARAM, timeout=self.comm_timeout)
                    if ret:
                        WorkerWifi.queue_msg.put((self.ip_port, msg_detail))
                self.query_desc = None
        # 从字典删除该TCP连接
        del WorkerWifi.dict_clients[self.ip_port]
        print("Radar Disconnected:", self.ip_port)
        WorkerWifi.queue_radar_disconnect.put(self.ip_port)

    def get_msg485(self, cmd_code, timeout=0.2):
        # 收消息，有超时时间
        time_now = time.time()
        cache_485 = bytes()
        while time.time() - time_now < timeout:
            data = self.recv(128)
            if data is not None and len(data) > 0:
                cache_485 += data
                cache_485, msgs_485 = Msg485Recv.parse_data(cache_485)
                for msg_485 in msgs_485:
                    if msg_485.is_msg(cmd_code):
                        msg_detail = MsgDetail.parse_data(cmd_code, msg_485.frame_data)
                        return True, msg_detail
            else:
                time.sleep(0.005)
        return False, None

    def send_cfg_cmds(self):
        ret_desc = ""
        cur_cmd_idx = 1
        for cmd in self.cfg_cmds:
            # 发送命令
            self.send(bytes(cmd + "\n", "utf-8"))
            if cmd == "closeWifi":
                # 对关闭wifi做特殊超时处理
                ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=5)
            else:
                ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=self.comm_timeout)
            if not ret:
                ret_desc += cmd + " : no data received\r\n"
            elif msg_detail.response != 0x01:
                ret_desc += cmd + " : %02X" % msg_detail.response + "\r\n"
            WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_CFG,
                                                int(cur_cmd_idx * 100 / len(self.cfg_cmds))))
            cur_cmd_idx += 1
        WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_CFG, ret_desc))

    def update_firmware(self):
        ret_desc = ""
        # 1. 发送ReadyUpdate
        ret = False
        for i in range(5):
            self.send(bytes("ReadyUpdate\n", "utf-8"))
            ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=1)
            if ret and msg_detail.response == 0x21 and msg_detail.crc == 0xcb:
                ret = True
                break
        if not ret:
            ret_desc = "ReadyUpdate命令未收到响应"
        else:
            WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_FIRM, 10))
            # 2. 发送Update
            self.send(bytes("Update\n", "utf-8"))
            ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=15)
            if not ret or msg_detail.response != 0x22 or msg_detail.crc != 0xcc:
                ret_desc = "Update命令未收到响应"
            else:
                WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_FIRM, 20))
                # 3. XModem协议传输文件
                file = open(self.firm_path, "rb")
                file_size = os.path.getsize(self.firm_path)
                packet_num = math.ceil(file_size / WorkerWifi.packet_size)

                def getc(size, timeout=5):
                    cache = bytes()
                    x_time = time.time()
                    while time.time() - x_time < timeout:
                        data = self.recv(size)
                        if data is not None and len(data) > 0:
                            cache += data
                            if len(cache) >= size:
                                return cache[0: size]
                        else:
                            time.sleep(0.005)
                    return None

                def putc(data, timeout=1):
                    return self.send(data)

                def callback_func(total_packets, success_count, error_count):
                    WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_FIRM,
                                                        20 + int(success_count * 70 / packet_num)))

                if WorkerWifi.packet_size == 128:
                    xmodem = XMODEM(getc, putc, mode='xmodem')
                else:
                    xmodem = XMODEM(getc, putc, mode='xmodem1k')
                xmodem_ret = xmodem.send(file, timeout=5, callback=callback_func)
                file.close()
                if not xmodem_ret:
                    ret_desc = "XModem传输错误"
                else:
                    # 4. 确认响应
                    ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=15)
                    if not ret or msg_detail.response != 0x23 or msg_detail.crc != 0xcd:
                        ret_desc = "未收到固件更新完成响应"
                    else:
                        WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_FIRM, 100))
        WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_FIRM, ret_desc))

    def update_sbl(self):
        ret_desc = ""
        # 1. 发送sbl升级请求
        file_size = os.path.getsize(self.sbl_path)
        packet_num = math.ceil(file_size / WorkerWifi.packet_size)
        self.send(bytes("updateSbl %d\n" % file_size, "utf-8"))
        ret, msg_detail = self.get_msg485(CMD_485_OTA, timeout=15)
        if not ret:
            ret_desc = "updateSbl命令未收到响应"
        elif msg_detail.response != 0x01:
            ret_desc = "updateSbl命令响应错误 : %02X" % msg_detail.response
        else:
            WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_SBL, 10))
            # 2. 传输文件
            file = open(self.sbl_path, "rb")
            for i in range(packet_num):
                if i < packet_num - 1:
                    cmd_bytes = file.read(WorkerWifi.packet_size)
                else:
                    cmd_bytes = file.read()
                for j in range(5):
                    self.send(Msg485Send(1, frame_idx=i+1).get_cmd(CMD_485_SBL, cmd_bytes))
                    ret, msg_detail = self.get_msg485(CMD_485_SBL, timeout=5)
                    if not ret:
                        ret_desc = "sbl升级包未收到响应"
                    elif msg_detail.response != 0x01:
                        ret_desc = "sbl升级包响应错误 : %02X" % msg_detail.response
                    else:
                        ret_desc = ""
                        WorkerWifi.queue_progress_rate.put((self.ip_port, PROGRESS_TYPE_SBL, 10 + int((i + 1) * 90 / packet_num)))
                        break
                if ret_desc != "":
                    break
            file.close()
        WorkerWifi.queue_progress_rets.put((self.ip_port, PROGRESS_TYPE_SBL, ret_desc))


class WifiTCPServer(QtCore.QThread):
    def __init__(self, server):
        """
        构造函数
        """
        super(WifiTCPServer, self).__init__()
        self.server = server

    def end(self):
        """
        停止接收数据
        """
        self.server.shutdown()
        self.server.server_close()
        return True

    def run(self):
        self.server.serve_forever()


class WorkerWifi(WorkerBase):
    """
    网络数据接收器
    """
    # TCP连接字典
    dict_clients = {}
    # 线程共享数据
    queue_msg = Queue()
    queue_progress_rate = Queue()
    queue_progress_rets = Queue()
    queue_radar_disconnect = Queue()
    #
    radar_timeout = 1
    comm_timeout = 0.2
    packet_size = 128
    debug_target = False
    detail_target = False

    def __init__(self, ip, port, radar_timeout=1, comm_timeout=0.2, debug_target=False, detail_target=False, packet_size=128):
        """
        构造函数
        """
        super(WorkerWifi, self).__init__()
        self.ip = ip
        self.port = port
        self.tcp_server = None
        WorkerWifi.debug_target = debug_target
        WorkerWifi.detail_target = detail_target
        WorkerWifi.radar_timeout = radar_timeout
        WorkerWifi.comm_timeout = comm_timeout
        WorkerWifi.packet_size = packet_size

    def query(self, query_desc):
        self.query_desc = query_desc

    def cfg_config(self, cfg_cmds, cfg_filter):
        """
        cfg配置
        :param cfg_cmds:
        :param cfg_filter:
        :return:
        """
        self.cfg_cmds = cfg_cmds.split("\n")
        self.cfg_filter = cfg_filter

    def firm_update(self, firm_path, firm_filter):
        """
        固件更新
        :param firm_path:
        :param firm_filter:
        :return:
        """
        self.firm_path = firm_path
        self.firm_filter = firm_filter

    def sbl_update(self, sbl_path, sbl_filter):
        self.sbl_path = sbl_path
        self.sbl_filter = sbl_filter

    def init(self):
        """
        测试网络是否能够正常连接
        :return:
        """
        try:
            socketserver.TCPServer.allow_reuse_address = True
            server = socketserver.ThreadingTCPServer((self.ip, self.port), WifiTCPHandler)
            self.tcp_server = WifiTCPServer(server)
        except Exception as e:
            print(e)
            return False
        return True

    def kick_client(self, desc):
        if desc in WorkerWifi.dict_clients.keys():
            WorkerWifi.dict_clients[desc].end()

    def kick_all_client(self):
        for desc, client in WorkerWifi.dict_clients.items():
            client.end()

    def reset_descs(self, ids_485):
        return

    def add_485id(self, id_485):
        return

    def del_485id(self, id_485):
        self.kick_client(id_485)

    def run(self):
        self.tcp_server.start()
        while self.is_run:
            try:
                time.sleep(0.005)
                # 消息通知
                while not WorkerWifi.queue_msg.empty():
                    p = WorkerWifi.queue_msg.get()
                    self.msg_signal.emit(p[0], p[1])
                # 发送cfg配置
                if self.cfg_cmds is not None:
                    descs = []
                    for desc, tcp_client in WorkerWifi.dict_clients.items():
                        if desc in self.cfg_filter:
                            tcp_client.cfg_cmds = self.cfg_cmds
                            descs.append(desc)
                    self.cfg_cmds = None
                    self.queue_progress_rets.put(("", PROGRESS_TYPE_CFG, ";".join(descs)))
                # update firmware
                if self.firm_path is not None:
                    descs = []
                    for desc, tcp_client in WorkerWifi.dict_clients.items():
                        if desc in self.firm_filter:
                            tcp_client.firm_path = self.firm_path
                            descs.append(desc)
                    self.firm_path = None
                    self.queue_progress_rets.put(("", PROGRESS_TYPE_FIRM, ";".join(descs)))
                # update firmware
                if self.sbl_path is not None:
                    descs = []
                    for desc, tcp_client in WorkerWifi.dict_clients.items():
                        if desc in self.sbl_filter:
                            tcp_client.sbl_path = self.sbl_path
                            descs.append(desc)
                    self.sbl_path = None
                    self.queue_progress_rets.put(("", PROGRESS_TYPE_SBL, ";".join(descs)))
                #
                if self.query_desc is not None:
                    for desc, tcp_client in WorkerWifi.dict_clients.items():
                        if desc == self.query_desc:
                            tcp_client.query_desc = self.query_desc
                    self.query_desc = None
                #
                while not WorkerWifi.queue_progress_rate.empty():
                    p = WorkerWifi.queue_progress_rate.get()
                    self.progress_rate_signal.emit(p[0], p[1], p[2])
                while not WorkerWifi.queue_progress_rets.empty():
                    p = WorkerWifi.queue_progress_rets.get()
                    self.progress_result_signal.emit(p[0], p[1], p[2])
                # 客户端退出通知
                while not WorkerWifi.queue_radar_disconnect.empty():
                    p = WorkerWifi.queue_radar_disconnect.get()
                    self.client_exit_signal.emit(p)
            except Exception as e:
                print(e)
        self.kick_all_client()
        self.tcp_server.end()
        #
        WorkerWifi.dict_clients.clear()
        WorkerWifi.queue_msg.queue.clear()
        WorkerWifi.queue_progress_rate.queue.clear()
        WorkerWifi.queue_progress_rets.queue.clear()
        WorkerWifi.queue_radar_disconnect.queue.clear()
