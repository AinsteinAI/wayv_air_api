# -*- coding: utf-8 -*-
import serial
from worker.worker_base import *
from worker.msg.msg_485 import *
from worker.msg.msg_tlv import *
import time
import os
import math
from xmodem import XMODEM
from queue import Queue
import datetime


# 485通讯类
class Worker485(WorkerBase):

    def __init__(self, com, baud, ids_485, radar_timeout=1, comm_timeout=0.2, debug_target=False, detail_target=False, packet_size=128):
        super(Worker485, self).__init__()
        # 端口号 波特率
        self.com = com
        self.baud = baud
        #
        self.radar_timeout = radar_timeout
        self.comm_timeout = comm_timeout
        # 串口对象
        self.ser = None
        # 设备状态
        self.device_states = {}
        for id_485 in ids_485:
            self.device_states[id_485] = DeviceState()
        #
        self.new_ids_queue = Queue()
        # 点云模式
        self.cloud_mode = False
        self.cloud_cache = bytes()
        #
        self.debug_target = debug_target
        #
        self.detail_target = detail_target
        #
        self.cache_485 = bytes()
        #
        self.packet_size = packet_size

    def init(self):
        try:
            self.ser = serial.Serial(self.com, self.baud, timeout=0)
        except Exception as e:
            self.ser = None
            print(e)
            return False
        return True

    def flush(self):
        self.ser.flushInput()

    def send(self, data):
        # print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
        # print("send:", end="")
        # for b in data:
        #     print("%02x" % b, end=" ")
        # print("")
        self.ser.write(data)

    def recv(self, count):
        data = None
        try:
            data = self.ser.read(count)
        except serial.Timeout:
            pass
        # if data is not None and len(data) > 0:
            # print(datetime.datetime.now().strftime('%H:%M:%S.%f'), end=" ")
            # print("recv:", end="")
            # for b in data:
            #     print("%02x" % b, end=" ")
            # print("")
        return data

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

    def reset_descs(self, ids_485):
        self.new_ids_queue.put((ID_RESET, ids_485))

    def add_485id(self, id_485):
        self.new_ids_queue.put((ID_ADD, id_485))

    def del_485id(self, id_485):
        self.new_ids_queue.put((ID_DEL, id_485))

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

    def run(self):
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
                            self.msg_signal.emit(id_485, msg_detail)
                            ds.set_radar()
                if self.cloud_mode:
                    data = self.recv(512)
                    if data is not None:
                        self.cloud_cache += data
                        self.cloud_cache, msg_tlvs = MsgTlv.parse_data(self.cloud_cache)
                        for msg_tlv in msg_tlvs:
                            self.msg_signal.emit(id_485, msg_tlv)
                    # 点云模式 不做任何485协议交互
                    continue
                # 检测目标
                for id_485, ds in self.device_states.items():
                    if ds.is_radar() and ds.need_get_target():
                        if self.debug_target:
                            ret, msg_detail = self.communicate(id_485, CMD_485_DEBUG_TARGET, timeout=self.comm_timeout)
                        elif self.detail_target:
                            ret, msg_detail = self.communicate(id_485, CMD_485_DETAIL_TARGET, timeout=self.comm_timeout)
                        else:
                            ret, msg_detail = self.communicate(id_485, CMD_485_TARGET, timeout=self.comm_timeout)
                        if ret:
                            self.msg_signal.emit(id_485, msg_detail)
                            if ds.error_count > 200:
                                # 从错误状态变正常，让雷达重新获取版本号
                                ds.reset()
                            ds.error_count = 0
                        else:
                            if ds.error_count == 200:
                                # 正常变错误，需要通知界面
                                self.client_exit_signal.emit(id_485)
                            ds.error_count += 1
                # cfg配置
                if self.cfg_cmds is not None:
                    self.progress_result_signal.emit("", PROGRESS_TYPE_CFG, ";".join([x for x in self.cfg_filter]))
                    for id_485, ds in self.device_states.items():
                        if id_485 in self.cfg_filter:
                            self.__cfg_config_one(id_485, self.cfg_cmds)
                            ds.reset()
                    self.cfg_cmds = None
                    time.sleep(5)
                # 固件升级
                if self.firm_path is not None:
                    self.progress_result_signal.emit("", PROGRESS_TYPE_FIRM, ";".join([x for x in self.firm_filter]))
                    for id_485, ds in self.device_states.items():
                        if id_485 in self.firm_filter:
                            self.__firm_update_one(id_485, self.firm_path)
                            ds.reset()
                    self.firm_path = None
                # SBL升级
                if self.sbl_path is not None:
                    self.progress_result_signal.emit("", PROGRESS_TYPE_SBL, ";".join([x for x in self.sbl_filter]))
                    for id_485, ds in self.device_states.items():
                        if id_485 in self.sbl_filter:
                            self.__sbl_update_one(id_485, self.sbl_path)
                            ds.reset()
                    self.sbl_path = None
                # 查询
                if self.query_desc is not None:
                    for id_485, ds in self.device_states.items():
                        if id_485 == self.query_desc and ds.is_radar():
                            ret, msg_detail = self.communicate(id_485, CMD_485_CONFIG, timeout=self.comm_timeout)
                            if ret:
                                self.msg_signal.emit(id_485, msg_detail)
                            ret, msg_detail = self.communicate(id_485, CMD_485_PARAM, timeout=self.comm_timeout)
                            if ret:
                                self.msg_signal.emit(id_485, msg_detail)
                    self.query_desc = None
        except Exception as e:
            print(e)
        try:
            self.ser.close()
        except Exception as e:
            print(e)

    def communicate(self, id_485, cmd_code, frame_data=bytes(), timeout=0.2, frame_idx=0):
        id_485 = int(id_485)
        # 发送消息
        self.flush()
        self.cache_485 = bytes()
        bs = Msg485Send(id_485, frame_idx=frame_idx).get_cmd(cmd_code, frame_data)
        self.send(bs)
        return self.get_msg485(id_485, cmd_code, timeout)

    def get_msg485(self, id_485, cmd_code, timeout=0.2):
        # 收消息，有超时时间
        time_now = time.time()
        while time.time() - time_now < timeout:
            data = self.recv(128)
            if data is not None and len(data) > 0:
                self.cache_485 += data
                self.cache_485, msgs_485 = Msg485Recv.parse_data(self.cache_485)
                for msg_485 in msgs_485:
                    if msg_485.id_485 == id_485 and msg_485.is_msg(cmd_code):
                        msg_detail = MsgDetail.parse_data(cmd_code, msg_485.frame_data)
                        return True, msg_detail
            else:
                time.sleep(0.005)
        return False, None

    def __cfg_config_one(self, id_485, cfg_cmds):
        ret_desc = ""
        cur_cmd_idx = 1
        for cmd in cfg_cmds:
            time.sleep(0.005)
            cmd_bytes = bytes(cmd + "\n", "utf-8")
            if cmd == "closeWifi":
                # 对关闭wifi做特殊超时处理
                ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=5)
            else:
                ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=self.comm_timeout)
            if not ret:
                ret_desc += cmd + " : no data received\r\n"
            elif msg_detail.response != 0x01:
                ret_desc += cmd + " : %02X" % msg_detail.response + "\r\n"
            self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_CFG, int(cur_cmd_idx * 100 / len(cfg_cmds)))
            cur_cmd_idx += 1
        self.progress_result_signal.emit(id_485, PROGRESS_TYPE_CFG, ret_desc)

    def __firm_update_one(self, id_485, firm_path):
        ret_desc = ""
        # 1. 发送ReadyUpdate 最多尝试5次
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
            self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_FIRM, 10)
            # 2. 发送Update
            cmd_bytes = bytes("Update\n", "utf-8")
            ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=20)
            if not ret or msg_detail.response != 0x22 or msg_detail.crc != 0xcc:
                ret_desc = "Update命令未收到响应"
            else:
                self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_FIRM, 20)
                # 3. XModem协议传输文件
                file = open(firm_path, "rb")
                file_size = os.path.getsize(firm_path)
                packet_num = math.ceil(file_size / self.packet_size)

                def getc(size, timeout=1):
                    r, m = self.get_msg485(int(id_485), CMD_485_OTA_XMODEM, timeout=timeout)
                    if r and len(m.data) == size:
                        return m.data
                    else:
                        return None

                def putc(data, timeout=1):
                    time.sleep(0.005)
                    bs = Msg485Send(int(id_485)).get_cmd(CMD_485_OTA_XMODEM, data)
                    return self.send(bs)

                def callback_func(total_packets, success_count, error_count):
                    self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_FIRM, 20 + int(success_count * 70 / packet_num))

                if self.packet_size == 128:
                    xmodem = XMODEM(getc, putc, mode='xmodem')
                else:
                    xmodem = XMODEM(getc, putc, mode='xmodem1k')
                xmodem_ret = xmodem.send(file, timeout=2, callback=callback_func)
                file.close()
                if not xmodem_ret:
                    ret_desc = "XModem传输错误"
                else:
                    # 4. 确认响应
                    ret, msg_detail = self.get_msg485(int(id_485), CMD_485_OTA, timeout=15)
                    if not ret or msg_detail.response != 0x23 or msg_detail.crc != 0xcd:
                        ret_desc = "未收到固件更新完成响应"
                    else:
                        self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_FIRM, 100)
        self.progress_result_signal.emit(id_485, PROGRESS_TYPE_FIRM, ret_desc)

    def __sbl_update_one(self, id_485, sbl_path):
        ret_desc = ""
        # 1. 发送sbl升级请求
        file_size = os.path.getsize(sbl_path)
        packet_num = math.ceil(file_size / self.packet_size)
        cmd_bytes = bytes("updateSbl %d\n" % file_size, "utf-8")
        ret, msg_detail = self.communicate(id_485, CMD_485_OTA, cmd_bytes, timeout=15)
        if not ret:
            ret_desc = "updateSbl命令未收到响应"
        elif msg_detail.response != 0x01:
            ret_desc = "updateSbl命令响应错误 : %02X" % msg_detail.response
        else:
            self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_SBL, 10)
            # 2. 传输文件
            file = open(sbl_path, "rb")
            for i in range(packet_num):
                if i < packet_num - 1:
                    cmd_bytes = file.read(self.packet_size)
                else:
                    cmd_bytes = file.read()
                for j in range(5):
                    time.sleep(0.005)
                    ret, msg_detail = self.communicate(id_485, CMD_485_SBL, cmd_bytes, timeout=1, frame_idx=i+1)
                    if not ret:
                        ret_desc = "sbl升级包未收到响应"
                    elif msg_detail.response != 0x01:
                        ret_desc = "sbl升级包响应错误 : %02X" % msg_detail.response
                    else:
                        ret_desc = ""
                        self.progress_rate_signal.emit(id_485, PROGRESS_TYPE_SBL, 10 + int((i + 1) * 90 / packet_num))
                        break
                if ret_desc != "":
                    break
            file.close()
        self.progress_result_signal.emit(id_485, PROGRESS_TYPE_SBL, ret_desc)
