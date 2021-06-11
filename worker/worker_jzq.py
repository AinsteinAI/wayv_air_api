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
from queue import Queue
from worker.msg.msg_jzq import *
from worker.msg.msg_485 import *
from worker.msg.msg_detail import *
import os
import math
from xmodem import XMODEM
import socket
from worker.worker_base import *
import datetime
import threading


class LineThread(Thread):

    def __init__(self, ip_port, line_id, tcp_handler, radar_timeout=1, comm_timeout=0.2, xmodem1k=False):
        super(LineThread, self).__init__()
        # ip
        self.ip_port = ip_port
        # 线路id
        self.line_id = line_id
        # 数据层
        self.tcp_handler = tcp_handler
        #
        self.radar_timeout = radar_timeout
        self.comm_timeout = comm_timeout
        # 485id列表
        self.device_states = {}
        self.new_ids_queue = Queue()
        #
        self.is_run = True
        # 消息接收列表
        self.recv_queue = Queue()
        # CFG配置命令
        self.cfg_cmds = None
        # CFGG过滤器
        self.cfg_filter = None
        # 固件路径
        self.firm_path = None
        self.firm_filter = None
        #
        self.sbl_path = None
        self.sbl_filter = None
        #
        self.query_desc = None
        # 是否以1k包进行xmodem传输
        self.xmodem1k = xmodem1k

    def get_desc(self, id_485):
        return self.ip_port + "-" + str(self.line_id) + "-" + str(id_485)

    def sync_485id(self):
        while not self.new_ids_queue.empty():
            tup = self.new_ids_queue.get()
            if tup[0] == ID_RESET:
                for value in self.device_states.values():
                    value.reset()
                for id_485 in tup[1]:
                    if id_485 not in self.device_states.keys():
                        self.device_states[id_485] = DeviceState()
            elif tup[0] == ID_ADD:
                self.device_states[tup[1]] = DeviceState()
            elif tup[0] == ID_DEL:
                self.device_states.pop(tup[1])

    def end(self):
        self.is_run = False
        self.wait()
        return True

    def cfg_config(self, cfg_cmds, cfg_filter):
        self.cfg_cmds = cfg_cmds
        self.cfg_filter = cfg_filter

    def firm_update(self, firm_path, firm_filter):
        self.firm_path = firm_path
        self.firm_filter = firm_filter

    def sbl_update(self, sbl_path, sbl_filter):
        self.sbl_path = sbl_path
        self.sbl_filter = sbl_filter

    def run(self):
        ids_485 = [int(x[x.rfind("-") + 1:]) for x in WorkerJzq.client_descs if
                   x.startswith(self.ip_port + "-" + str(self.line_id))]
        for id_485 in ids_485:
            self.device_states[id_485] = DeviceState()
        print("line created -- %s" % self.line_id)
        #
        try:
            while self.is_run:
                time.sleep(0.005)
                # 同步485id
                self.sync_485id()
                # 检测版本
                for id_485, ds in self.device_states.items():
                    if ds.need_get_version():
                        ret, msg_detail = self.communicate(id_485, CMD_485_VERSION, bytes(), timeout=self.radar_timeout)
                        if ret:
                            WorkerJzq.queue_msg.put((self.get_desc(id_485), msg_detail))
                            ds.set_radar()
                # 获取目标
                for id_485, ds in self.device_states.items():
                    if ds.is_radar() and ds.need_get_target():
                        if WorkerJzq.debug_target:
                            ret, msg_detail = self.communicate(id_485, CMD_485_DEBUG_TARGET, timeout=self.comm_timeout)
                        else:
                            ret, msg_detail = self.communicate(id_485, CMD_485_TARGET, timeout=self.comm_timeout)
                        if ret:
                            WorkerJzq.queue_msg.put((self.get_desc(id_485), msg_detail))
                            if ds.error_count > 200:
                                # 从错误状态变正常，让雷达重新获取版本号
                                ds.reset()
                            ds.error_count = 0
                        else:
                            if ds.error_count == 200:
                                # 正常变错误，需要通知界面
                                WorkerJzq.queue_radar_disconnect.put(self.get_desc(id_485))
                            ds.error_count += 1
                # CFG配置
                if self.cfg_cmds is not None:
                    for id_485, ds in self.device_states.items():
                        if self.get_desc(id_485) in self.cfg_filter:
                            self.__cfg_config_one(id_485, self.cfg_cmds)
                            ds.reset()
                    self.cfg_cmds = None
                # 固件升级
                if self.firm_path is not None:
                    for id_485, ds in self.device_states.items():
                        if self.get_desc(id_485) in self.firm_filter:
                            self.__firm_update_one(id_485, self.firm_path)
                            ds.reset()
                    self.firm_path = None
                # 固件升级
                if self.sbl_path is not None:
                    for id_485, ds in self.device_states.items():
                        if self.get_desc(id_485) in self.sbl_filter:
                            self.__sbl_update_one(id_485, self.sbl_path)
                            ds.reset()
                    self.sbl_path = None
                #
                if self.query_desc is not None:
                    for id_485, ds in self.device_states.items():
                        if self.get_desc(id_485) == self.query_desc:
                            if ds.is_radar():
                                ret, msg_detail = self.communicate(id_485, CMD_485_CONFIG, timeout=self.comm_timeout)
                                if ret:
                                    WorkerJzq.queue_msg.put((self.get_desc(id_485), msg_detail))
                                ret, msg_detail = self.communicate(id_485, CMD_485_PARAM, timeout=self.comm_timeout)
                                if ret:
                                    WorkerJzq.queue_msg.put((self.get_desc(id_485), msg_detail))
                    self.query_desc = None
        except Exception as e:
            print(e)
        print("line exit -- %s" % self.line_id)

    def communicate(self, id_485, cmd_code, frame_data=bytes(), timeout=0.2, frame_idx=0):
        # 发送消息
        msg = MsgJZQSend(self.line_id)
        msg.set_data(Msg485Send(id_485, frame_idx=frame_idx).get_cmd(cmd_code, frame_data))
        self.recv_queue.queue.clear()
        self.tcp_handler.send_queue.put(msg.get_bytes())
        return self.get_msg485(id_485, cmd_code, timeout)

    def get_msg485(self, id_485, cmd_code, timeout=0.2):
        # 收消息，有超时时间
        time_now = time.time()
        while time.time() - time_now < timeout:
            if not self.recv_queue.empty():
                msg_485 = self.recv_queue.get()
                if msg_485.id_485 == id_485 and msg_485.is_msg(cmd_code):
                    msg_detail = MsgDetail.parse_data(cmd_code, msg_485.frame_data)
                    return True, msg_detail
            else:
                time.sleep(0.005)
        return False, None

    def __cfg_config_one(self, id_485, cfg_cmds):
        if self.cfg_cmds is not None:
            ret_desc = ""
            cur_cmd_idx = 1
            for cmd in cfg_cmds:
                cmd_bytes = bytes(cmd + "\n", "utf-8")
                ret, msg_ota = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=self.comm_timeout)
                if not ret:
                    ret_desc += cmd + " : no data received\r\n"
                elif msg_ota.response != 0x01:
                    ret_desc += cmd + " : %02X" % msg_ota.response + "\r\n"
                WorkerJzq.pro_rate_queue.put(
                    (self.get_desc(id_485), PROGRESS_TYPE_CFG, int(cur_cmd_idx * 100 / len(cfg_cmds))))
            WorkerJzq.pro_ret_queue.put((self.get_desc(id_485), PROGRESS_TYPE_CFG, ret_desc))

    def __firm_update_one(self, id_485, firm_path):
        ret_desc = ""
        # 1. 发送ReadyUpdate
        ret = False
        cmd_bytes = bytes("ReadyUpdate\n", "utf-8")
        for i in range(5):
            ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=1)
            if ret and msg_detail.response == 0x21 and msg_detail.crc == 0xcb:
                ret = True
                break
        if not ret:
            ret_desc = "ReadyUpdate命令未收到响应"
        else:
            WorkerJzq.pro_rate_queue.put((self.get_desc(id_485), PROGRESS_TYPE_FIRM, 10))
            # 2. 发送Update
            cmd_bytes = bytes("Update\n", "utf-8")
            ret, msg_ota = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=20)
            if not ret or msg_ota.response != 0x22 or msg_ota.crc != 0xcc:
                ret_desc = "Update命令未收到响应"
            else:
                WorkerJzq.pro_rate_queue.put((self.get_desc(id_485), PROGRESS_TYPE_FIRM, 20))
                # 3. XModem协议传输文件
                file = open(firm_path, "rb")
                file_size = os.path.getsize(firm_path)
                packet_num = math.ceil(file_size / WorkerJzq.packet_size)

                def getc(size, timeout=1):
                    # print("getc", end=" ")
                    r, m = self.get_msg485(id_485, CMD_485_OTA_XMODEM, timeout)
                    if r and len(m.data) == size:
                        # for b in m.data:
                        #     print("%c" % b, end="")
                        #     print("")
                        return m.data
                    else:
                        # print("")
                        return None

                def putc(data, timeout=1):
                    msg = MsgJZQSend(self.line_id)
                    msg.set_data(Msg485Send(id_485).get_cmd(CMD_485_OTA_XMODEM, data))
                    self.recv_queue.queue.clear()
                    self.tcp_handler.send_queue.put(msg.get_bytes())
                    time.sleep(0.005)
                    return

                def callback_func(total_packets, success_count, error_count):
                    WorkerJzq.pro_rate_queue.put(
                        (self.get_desc(id_485), PROGRESS_TYPE_FIRM, 20 + int(success_count * 70 / packet_num)))

                try:
                    if WorkerJzq.packet_size == 128:
                        xmodem = XMODEM(getc, putc, mode='xmodem')
                    else:
                        xmodem = XMODEM(getc, putc, mode='xmodem1k')
                    xmodem_ret = xmodem.send(file, timeout=2, callback=callback_func)
                except Exception as e:
                    print(e)
                file.close()
                if not xmodem_ret:
                    ret_desc = "XModem传输错误"
                else:
                    # 4. 确认响应
                    ret, msg_ota = self.get_msg485(id_485, CMD_485_OTA, 15)
                    if not ret or msg_ota.response != 0x23 or msg_ota.crc != 0xcd:
                        ret_desc = "未收到固件更新完成响应"
                    else:
                        WorkerJzq.pro_rate_queue.put((self.get_desc(id_485), PROGRESS_TYPE_FIRM, 100))
        WorkerJzq.pro_ret_queue.put((self.get_desc(id_485), PROGRESS_TYPE_FIRM, ret_desc))

    def __sbl_update_one(self, id_485, sbl_path):
        ret_desc = ""
        # 1. 发送sbl升级请求
        file_size = os.path.getsize(sbl_path)
        packet_num = math.ceil(file_size / WorkerJzq.packet_size)
        cmd_bytes = bytes("updateSbl %d\n" % file_size, "utf-8")
        ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=15)
        if not ret:
            ret_desc = "updateSbl命令未收到响应"
        elif msg_detail.response != 0x01:
            ret_desc = "updateSbl命令响应错误 : %02X" % msg_detail.response
        else:
            WorkerJzq.pro_rate_queue.put((self.get_desc(id_485), PROGRESS_TYPE_SBL, 10))
            # 2. 传输文件
            file = open(sbl_path, "rb")
            for i in range(packet_num):
                if i < packet_num - 1:
                    cmd_bytes = file.read(WorkerJzq.packet_size)
                else:
                    cmd_bytes = file.read()
                for j in range(5):
                    ret, msg_detail = self.communicate(id_485, CMD_485_SBL, cmd_bytes, timeout=1, frame_idx=i + 1)
                    if not ret:
                        ret_desc = "sbl升级包未收到响应"
                    elif msg_detail.response != 0x01:
                        ret_desc = "sbl升级包响应错误 : %02X" % msg_detail.response
                    else:
                        ret_desc = ""
                        WorkerJzq.pro_rate_queue.put((self.get_desc(id_485), PROGRESS_TYPE_SBL, 10 + int((i + 1) * 90 / packet_num)))
                        break
                if ret_desc != "":
                    break
            file.close()
        WorkerJzq.pro_ret_queue.put((self.get_desc(id_485), PROGRESS_TYPE_SBL, ret_desc))


class JzqTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        # 485线路id列表
        self.ids_line = [1, 2, 3, 4]
        self.recv_queues = {}
        self.caches_485 = {}
        for line_id in self.ids_line:
            self.recv_queues[line_id] = Queue()
            self.caches_485[line_id] = bytes()
        #
        self.is_run = True
        # 发送队列 集中器协议消息
        self.send_queue = Queue()
        #
        self.line_threads = {}
        #
        self.cfg_cmds = None
        self.cfg_filter = None
        self.firm_path = None
        self.firm_filter = None
        self.sbl_path = None
        self.sbl_filter = None
        self.query_desc = None
        #
        self.ip_port = ""
        #
        self.alive_time = 0
        super(JzqTCPHandler, self).__init__(request, client_address, server)

    def send(self, data):
        print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
        print("send:", end="")
        for b in data:
            print("%02x " % b, end="")
        print("")
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
            print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
            print("recv:", end="")
            for b in data:
                print("%02x " % b, end="")
            print("")
        return data

    def end(self):
        self.is_run = False

    def cfg_config(self, cfg_cmds, cfg_filter):
        self.cfg_cmds = cfg_cmds
        self.cfg_filter = cfg_filter

    def firm_update(self, firm_path, firm_filter):
        self.firm_path = firm_path
        self.firm_filter = firm_filter

    def sbl_update(self, sbl_path, sbl_filter):
        self.sbl_path = sbl_path
        self.sbl_filter = sbl_filter

    def reset_descs(self, descs):
        for id_line in self.ids_line:
            ids_485 = [int(x[x.rfind("-") + 1:]) for x in descs if x.startswith(self.ip_port + "-" + str(id_line))]
            if len(ids_485) > 0:
                self.line_threads[id_line].new_ids_queue.put((ID_RESET, ids_485))

    def add_485id(self, desc):
        line = int(desc.split("-")[1])
        id_485 = int(desc.split("-")[2])
        self.line_threads[line].new_ids_queue.put((ID_ADD, id_485))

    def del_485id(self, desc):
        line = int(desc.split("-")[1])
        id_485 = int(desc.split("-")[2])
        self.line_threads[line].new_ids_queue.put((ID_DEL, id_485))

    def handle(self):
        cache_jzq = bytes()
        # 一个集中器连接
        self.ip_port = self.client_address[0]
        if self.ip_port in WorkerJzq.ip_clients.keys():
            WorkerJzq.ip_clients[self.ip_port].end()
            time.sleep(2)
        WorkerJzq.ip_clients[self.ip_port] = self
        print("jizhongqi connected -- %s" % self.ip_port)
        WorkerJzq.queue_msg.put((self.ip_port, MsgVersion()))
        # 设置超时时间
        self.request.settimeout(0.005)
        # 不同485线路之间并行,同一485线路上串行,所以一条485线路需要启一个线程
        for id_line in self.ids_line:
            self.line_threads[id_line] = LineThread(self.ip_port, id_line, self,
                                                    WorkerJzq.radar_timeout, WorkerJzq.comm_timeout)
            self.line_threads[id_line].start()
        #
        self.alive_time = time.time()
        # 主循环
        try:
            while self.is_run:
                if time.time() - self.alive_time >= 40:
                    print("not alive")
                    break
                # 发送数据
                while not self.send_queue.empty():
                    self.send(self.send_queue.get())
                # 接收解析数据
                data = self.recv(1024)
                if data is not None and len(data) > 0:
                    cache_jzq += data
                    # 解析集中器协议数据包
                    cache_jzq, msgs_jzq = MsgJZQRecv.parse_data(cache_jzq)
                    for msg_jzq in msgs_jzq:
                        self.caches_485[msg_jzq.id_line] += msg_jzq.data
                        self.caches_485[msg_jzq.id_line], msgs_485 = Msg485Recv.parse_data(
                            self.caches_485[msg_jzq.id_line])
                        for msg_485 in msgs_485:
                            self.line_threads[msg_jzq.id_line].recv_queue.put(msg_485)
                #
                if self.cfg_cmds is not None:
                    for line_thread in list(self.line_threads.values()):
                        line_thread.cfg_config(self.cfg_cmds, self.cfg_filter)
                    self.cfg_cmds = None
                    self.cfg_filter = None
                #
                if self.firm_path is not None:
                    for line_thread in list(self.line_threads.values()):
                        line_thread.firm_update(self.firm_path, self.firm_filter)
                    self.firm_path = None
                    self.firm_filter = None
                #
                if self.sbl_path is not None:
                    for line_thread in list(self.line_threads.values()):
                        line_thread.sbl_update(self.sbl_path, self.sbl_filter)
                    self.sbl_path = None
                    self.sbl_filter = None
                #
                if self.query_desc is not None:
                    for line_thread in list(self.line_threads.values()):
                        line_thread.query_desc = self.query_desc
                    self.query_desc = None
                time.sleep(0.002)
        except Exception as e:
            print(e)
        # 停止线路线程
        for line_thread in self.line_threads.values():
            line_thread.end()
        for line_thread in self.line_threads.values():
            line_thread.wait()
        # 从字典删除该TCP连接
        del WorkerJzq.ip_clients[self.ip_port]
        print("jizhongqi disconnected -- %s" % self.ip_port)
        WorkerJzq.queue_radar_disconnect.put(self.ip_port)


class JzqTCPServer(Thread):
    def __init__(self, server):
        super(JzqTCPServer, self).__init__()
        self.server = server

    def end(self):
        self.server.shutdown()
        self.server.server_close()
        return True

    def run(self):
        self.server.serve_forever()


# 集中器通讯类
class WorkerJzq(WorkerBase):
    # TCP连接字典
    ip_clients = {}
    # 线程共享数据
    queue_msg = Queue()
    pro_rate_queue = Queue()
    pro_ret_queue = Queue()
    queue_radar_disconnect = Queue()
    #
    client_descs = []
    #
    radar_timeout = 1
    comm_timeout = 0.2
    #
    debug_target = False
    packet_size = False

    def __init__(self, ip, port, descs, radar_timeout=1, comm_timeout=0.2, debug_target=False, packet_size=128):
        super(WorkerJzq, self).__init__()
        self.ip = ip
        self.port = port
        self.tcp_server = None
        #
        WorkerJzq.client_descs = descs
        #
        WorkerJzq.radar_timeout = radar_timeout
        WorkerJzq.comm_timeout = comm_timeout
        #
        WorkerJzq.debug_target = debug_target
        WorkerJzq.packet_size = packet_size

    def query(self, query_desc):
        self.query_desc = query_desc

    def cfg_config(self, cfg_cmds, cfg_filter):
        self.cfg_cmds = cfg_cmds.split("\n")
        self.cfg_filter = cfg_filter

    def firm_update(self, firm_path, firm_filter):
        self.firm_path = firm_path
        self.firm_filter = firm_filter

    def sbl_update(self, sbl_path, sbl_filter):
        self.sbl_path = sbl_path
        self.sbl_filter = sbl_filter

    def add_485id(self, desc):
        WorkerJzq.client_descs.append(desc)
        ip = desc[0: desc.find("-")]
        if ip in WorkerJzq.ip_clients.keys():
            WorkerJzq.ip_clients[ip].add_485id(desc)

    def del_485id(self, desc):
        WorkerJzq.client_descs.remove(desc)
        ip = desc[0: desc.find("-")]
        if ip in WorkerJzq.ip_clients.keys():
            WorkerJzq.ip_clients[ip].del_485id(desc)

    def reset_descs(self, descs):
        for desc in descs:
            if desc not in WorkerJzq.client_descs:
                WorkerJzq.client_descs.append(desc)
        for ip, client in WorkerJzq.ip_clients.items():
            ip_descs = [x for x in descs if x.startswith(ip)]
            if len(ip_descs) > 0:
                client.reset_descs(ip_descs)

    def init(self):
        try:
            server = socketserver.ThreadingTCPServer((self.ip, self.port), JzqTCPHandler)
            self.tcp_server = JzqTCPServer(server)
        except Exception as e:
            print(e)
            return False
        return True

    def kick_client(self, desc):
        if desc in WorkerJzq.ip_clients.keys():
            WorkerJzq.dict_clients[desc].end()
            WorkerJzq.ip_clients.pop(desc)

    def kick_all_client(self):
        for desc, client in WorkerJzq.ip_clients.items():
            client.end()

    def run(self):
        print("jizhongqi tcp_server start")
        self.tcp_server.start()
        while self.is_run:
            try:
                time.sleep(0.005)
                # 消息通知
                while not WorkerJzq.queue_msg.empty():
                    p = WorkerJzq.queue_msg.get()
                    self.msg_signal.emit(p[0], p[1])
                # 发送cfg配置
                if self.cfg_cmds is not None:
                    cfg_filter = []
                    for ip, tcp_client in WorkerJzq.ip_clients.items():
                        tcp_client.cfg_config(self.cfg_cmds, self.cfg_filter)
                        cfg_filter.extend([x for x in self.cfg_filter if x.startswith(ip)])
                    self.pro_ret_queue.put(("", PROGRESS_TYPE_CFG, ";".join(cfg_filter)))
                    self.cfg_cmds = None
                    self.cfg_filter = None
                # update firmware
                if self.firm_path is not None:
                    firm_filter = []
                    for ip, tcp_client in WorkerJzq.ip_clients.items():
                        tcp_client.firm_update(self.firm_path, self.firm_filter)
                        firm_filter.extend([x for x in self.firm_filter if x.startswith(ip)])
                    self.pro_ret_queue.put(("", PROGRESS_TYPE_FIRM, ";".join(firm_filter)))
                    self.firm_path = None
                    self.firm_filter = None
                # update sbl
                if self.sbl_path is not None:
                    sbl_filter = []
                    for ip, tcp_client in WorkerJzq.ip_clients.items():
                        tcp_client.sbl_update(self.sbl_path, self.sbl_filter)
                        sbl_filter.extend([x for x in self.sbl_filter if x.startswith(ip)])
                    self.pro_ret_queue.put(("", PROGRESS_TYPE_SBL, ";".join(sbl_filter)))
                    self.sbl_path = None
                    self.sbl_filter = None
                #
                if self.query_desc is not None:
                    for ip, tcp_client in WorkerJzq.ip_clients.items():
                        if ip in self.query_desc:
                            tcp_client.query_desc = self.query_desc
                    self.query_desc = None
                #
                while not WorkerJzq.pro_rate_queue.empty():
                    p = WorkerJzq.pro_rate_queue.get()
                    self.progress_rate_signal.emit(p[0], p[1], p[2])
                while not WorkerJzq.pro_ret_queue.empty():
                    p = WorkerJzq.pro_ret_queue.get()
                    self.progress_result_signal.emit(p[0], p[1], p[2])
                # 客户端退出通知
                while not WorkerJzq.queue_radar_disconnect.empty():
                    p = WorkerJzq.queue_radar_disconnect.get()
                    self.client_exit_signal.emit(p)
            except Exception as e:
                print(e)
        self.kick_all_client()
        self.tcp_server.end()
        #
        WorkerJzq.ip_clients.clear()
        WorkerJzq.queue_msg.queue.clear()
        WorkerJzq.pro_rate_queue.queue.clear()
        WorkerJzq.pro_ret_queue.queue.clear()
        WorkerJzq.queue_radar_disconnect.queue.clear()
        #
        print("jizhongqi tcp_server stop")
