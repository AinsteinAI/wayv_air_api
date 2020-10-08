# -*- coding: utf-8 -*-
from receiver.receiver import Receiver
import socket
import socketserver
from PyQt5 import QtCore
from queue import Queue
import time
from xmodem import XMODEM
import struct
import os
import math
from crc import Crc
import logging
from model.project import GI

logger = logging.getLogger(GI.log_main_module + '.' + __name__)
logger.setLevel(GI.log_level)

# TCP连接字典
dict_clients = {}
# 线程共享数据
queue_client_raws = Queue()
queue_cfg_rets = Queue()
queue_cfg_progress = Queue()
queue_firm_rets = Queue()
queue_firm_progress = Queue()
#
queue_radar_disconnect = Queue()


class MyTCPHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.is_run = True
        self.cfg_cmds = None
        self.firmware_path = None
        self.timeout = 0.01
        self.xmodem = None
        self.ip_port = ""
        # 心跳检测间隔
        self.heartbeat_period = 3
        super(MyTCPHandler, self).__init__(request, client_address, server)

    def handle(self):
        last_heartbeat_time = 0
        print(self.tr("一个客户端连上来了"), self.client_address)
        # 将新的TCP连接记录到字典
        # self.ip_port = self.client_address[0] + ":" + str(self.client_address[1])
        self.ip_port = self.client_address[0]
        dict_clients[self.ip_port] = self
        # 设置超时时间为1s
        self.request.settimeout(self.timeout)

        # # 发送一帧空数据，告知主线程有客户端连上来了
        # queue_client_raws.put((self.ip_port, bytes()))

        def getc(size, timeout=1):
            data_recv = None
            # print("getc(%d):" % size, end="")
            try:
                data_recv = self.request.recv(size)
            except Exception as err:
                logger.error(err)
            # if data_recv is not None:
            #     for b in data_recv:
            #         print("%02x" % b, end="")
            #     print("")
            # print("")
            return data_recv

        def putc(data, timeout=1):
            # print("putc:", end="")
            # for b in data:
            #     print("%02x" % b, end="")
            # print("")
            return self.request.sendall(data)

        self.xmodem = XMODEM(getc, putc, mode='xmodem1k')

        # 主循环
        while self.is_run:
            # 心跳检测（获取版本号）
            if time.time() - last_heartbeat_time >= self.heartbeat_period:
                self.request.sendall(bytes("getVersion\n", "utf-8"))
                last_heartbeat_time = time.time()
            # 下发CFG
            try:
                self.send_cfg_cmds()
            except Exception as e:
                queue_cfg_rets.put((self.ip_port, str(e)))
                break
            # update firmware
            try:
                self.request.settimeout(1)
                self.update_firmware()
                self.request.settimeout(self.timeout)
            except Exception as e:
                queue_firm_rets.put((self.ip_port, str(e)))
                self.request.settimeout(self.timeout)
                break
            # 接收目标数据
            try:
                response = self.get_response(0.1)
                if response is not None:
                    queue_client_raws.put((self.ip_port, response))
                    # else:
                    #     # 没收到目标数据，检测客户端是否退出了
                    #     self.request.sendall(bytes("1", "utf-8"))
            except Exception as e:
                logger.error(e)
                break
        # 从字典删除该TCP连接
        del dict_clients[self.ip_port]
        print(self.tr("一个客户端退出去了"), self.ip_port)
        queue_radar_disconnect.put(self.ip_port)

    def send_cfg_cmds(self):
        if self.cfg_cmds is not None:
            str_cmds = self.cfg_cmds
            self.cfg_cmds = None
            ret_desc = ""
            cmds = str_cmds.split("\n")
            cur_cmd_idx = 1
            for cmd in cmds:
                # 发送命令
                self.request.sendall(bytes(cmd + "\n", "utf-8"))
                response = self.get_ota_response(1)
                # 获取应答
                if response is None:
                    ret_desc += cmd + " : no data received\r\n"
                elif response[1] != 0x01:
                    ret_desc += cmd + " : " + str(response[1]) + "\r\n"
                queue_cfg_progress.put((self.ip_port, int(cur_cmd_idx * 100 / len(cmds))))
                cur_cmd_idx += 1
            queue_cfg_rets.put((self.ip_port, ret_desc))

    def update_firmware(self):
        if self.firmware_path is not None:
            file_path = self.firmware_path
            self.firmware_path = None
            ret_desc = ""
            # 1. 发送ReadyUpdate
            self.request.sendall(bytes("ReadyUpdate\n", "utf-8"))
            if not self.get_exact_ota_response(b'\xAA\x21\xCB\x55', 10):
                ret_desc = self.tr("ReadyUpdate命令未收到响应")
            else:
                queue_firm_progress.put((self.ip_port, 10))
                # 2. 发送Update
                self.request.sendall(bytes("Update\n", "utf-8"))
                if not self.get_exact_ota_response(b'\xAA\x22\xCC\x55', 15):
                    ret_desc = self.tr("Update命令未收到响应")
                else:
                    queue_firm_progress.put((self.ip_port, 20))
                    # 3. XModem协议传输文件
                    file = open(file_path, "rb")
                    file_size = os.path.getsize(file_path)
                    packet_size = math.ceil(file_size / 1024)

                    def callback_func(total_packets, success_count, error_count):
                        queue_firm_progress.put((self.ip_port, 20 + int(success_count * 70 / packet_size)))

                    xmodem_ret = self.xmodem.send(file, callback=callback_func)
                    file.close()
                    if not xmodem_ret:
                        ret_desc = self.tr("XModem传输错误")
                    else:
                        # 4. 确认响应
                        if not self.get_exact_ota_response(b'\xAA\x23\xCD\x55', 15):
                            ret_desc = self.tr("未收到固件更新完成响应")
                        else:
                            queue_firm_progress.put((self.ip_port, 100))
            queue_firm_rets.put((self.ip_port, ret_desc))

    def get_response(self, timeout):
        idx = 0
        response = bytes()
        msg_len = -1
        start_time = time.time()
        while True:
            try:
                if time.time() - start_time > timeout:
                    break
                data = self.request.recv(1)
                if data is None or len(data) == 0:
                    raise Exception("client not exist")
                if idx < 4:
                    # 找包头标识 FF FF FF FF
                    if data[0] == 0xFF:
                        idx += 1
                    else:
                        idx = 0
                    if idx == 4:
                        response = bytes(b'\xFF\xFF\xFF\xFF')
                elif idx < 10:
                    # 读取包头
                    response += data
                    idx += 1
                    if idx == 10:
                        msg_len = struct.unpack('<H', response[8: 10])[0]
                elif idx < (10 + msg_len):
                    # 读取消息内容
                    response += data
                    idx += 1
                    if idx == (10 + msg_len):
                        break
            except socket.timeout:
                pass
        if msg_len != -1 and len(response) == (10 + msg_len):
            return response
        else:
            return None

    def get_ota_response(self, timeout):
        idx = 0
        response = bytes()
        msg_len = -1
        start_time = time.time()
        while True:
            try:
                if time.time() - start_time > timeout:
                    break
                data = self.request.recv(1)
                if data is None or len(data) == 0:
                    continue
                if idx < 4:
                    # 找包头标识 FF FF FF FF
                    if data[0] == 0xFF:
                        idx += 1
                    else:
                        idx = 0
                    if idx == 4:
                        response = bytes(b'\xFF\xFF\xFF\xFF')
                elif idx < 10:
                    # 读取包头
                    response += data
                    idx += 1
                    if idx == 10:
                        msg_len = struct.unpack('<H', response[8: 10])[0]
                elif idx < (10 + msg_len):
                    # 读取消息内容
                    response += data
                    idx += 1
                    if idx == (10 + msg_len):
                        # crc 校验
                        checksum = struct.unpack("<H", response[4: 6])[0]
                        calc_checksum = Crc.calc(response[6:])
                        # 需要确认命令码，ota应答为0x10
                        msg_cmd = struct.unpack('<B', response[13: 14])[0]
                        if checksum == calc_checksum and msg_cmd == 0x10:
                            break
                        else:
                            # print("checksum err or cmd is not 0x10")
                            idx = 0
                            response = bytes()
                            msg_len = -1
            except socket.timeout:
                pass
        if msg_len != -1 and len(response) == (10 + msg_len):
            # 消息内容里的应答数据是从整个包的第18个字节开始
            return response[18:]
        else:
            return None

    def get_exact_ota_response(self, result, timeout):
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                break
            response = self.get_ota_response(timeout - (time.time() - start_time))
            if response is not None and response == result:
                return True
        return False


class MyTCPServer(QtCore.QThread):
    def __init__(self, server):
        """
        构造函数
        """
        super(MyTCPServer, self).__init__()
        self.is_run = True
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


class ReceiverSocketServer(Receiver):
    """
    网络数据接收器
    """

    def __init__(self, ip, port):
        """
        构造函数
        """
        super(ReceiverSocketServer, self).__init__()
        self.ip = ip
        self.port = port
        self.my_tcp_server = None

    def prepare(self):
        """
        测试网络是否能够正常连接
        :return:
        """
        try:
            print(self.ip, self.port)
            server = socketserver.ThreadingTCPServer((self.ip, self.port), MyTCPHandler)
            self.my_tcp_server = MyTCPServer(server)
        except Exception as e:
            logger.error(e)
            return False
        return True

    def end(self):
        self.kick_all_client()
        #
        self.is_run = False
        self.wait()
        self.destroy()
        return True

    def kick_client(self, ip_port):
        if ip_port in dict_clients.keys():
            tcp_client = dict_clients[ip_port]
            tcp_client.is_run = False

    def kick_all_client(self):
        # 通知所有连接线程退出
        for tcp_client in dict_clients.values():
            tcp_client.is_run = False

    def send_cfg_cmds(self, cmds):
        cfg_clients = []
        cfg_filter_segs = None if self.cfg_filter is None else self.cfg_filter.split(";")
        for desc, tcp_client in dict_clients.items():
            if self.cfg_filter is None or desc in cfg_filter_segs:
                tcp_client.cfg_cmds = cmds
                cfg_clients.append(desc)
        self.cfg_filter = None
        queue_cfg_rets.put(("", ";".join(cfg_clients)))

    def update_firmware(self, file_path):
        firmware_clients = []
        firmware_filter_segs = None if self.firmware_filter is None else self.firmware_filter.split(";")
        for desc, tcp_client in dict_clients.items():
            if self.firmware_filter is None or desc in firmware_filter_segs:
                tcp_client.firmware_path = file_path
                firmware_clients.append(desc)
        self.firmware_filter = None
        queue_firm_rets.put(("", ";".join(firmware_clients)))

    def run(self):
        self.my_tcp_server.start()
        while self.is_run:
            if not self.is_pause:
                try:
                    # 发送cfg配置
                    if self.cfg_cmds is not None:
                        self.send_cfg_cmds(self.cfg_cmds)
                        self.cfg_cmds = None
                    # cfg配置结果通知
                    while not queue_cfg_rets.empty():
                        p = queue_cfg_rets.get()
                        self.cfg_result_signal.emit(p[0], p[1])
                    # cfg进度通知
                    while not queue_cfg_progress.empty():
                        p = queue_cfg_progress.get()
                        self.cfg_progress_signal.emit(p[0], p[1])
                    # update firmware
                    if self.firmware_path is not None:
                        self.update_firmware(self.firmware_path)
                        self.firmware_path = None
                    # 固件更新结果通知
                    while not queue_firm_rets.empty():
                        p = queue_firm_rets.get()
                        self.firm_result_signal.emit(p[0], p[1])
                    # 固件更新进度通知
                    while not queue_firm_progress.empty():
                        p = queue_firm_progress.get()
                        self.firm_progress_signal.emit(p[0], p[1])
                    # 接收数据
                    while not queue_client_raws.empty():
                        p = queue_client_raws.get()
                        self.data_signal.emit(p[0], p[1])
                    # 客户端退出通知
                    while not queue_radar_disconnect.empty():
                        self.client_exit_signal.emit(queue_radar_disconnect.get())
                except Exception as e:
                    logger.error(e)
            self.msleep(10)
        self.my_tcp_server.end()
        #
        dict_clients.clear()
        queue_client_raws.queue.clear()
        queue_cfg_rets.queue.clear()
        queue_cfg_progress.queue.clear()
        queue_firm_rets.queue.clear()
        queue_firm_progress.queue.clear()
        queue_radar_disconnect.queue.clear()
