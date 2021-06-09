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
from receiver.receiver import Receiver
import serial
import smokesignal
import struct
import time
from xmodem import XMODEM
import os
import math
from queue import Queue
from crc import Crc
import logging
from model.project import GI

logger = logging.getLogger(GI.log_main_module + '.' + __name__)
logger.setLevel(GI.log_level)


class ReceiverSerial485(Receiver):
    """
    串口数据接收器
    """

    def __init__(self, com, baud, ids_485, debug=False):
        """
        构造函数
        """
        super(ReceiverSerial485, self).__init__()

        self.com = com
        self.baud = baud
        self.ser = None
        self.ids_485 = ids_485
        self.to_send_queue = Queue()
        self.is_debug = debug
        self.query_normal = True
        self.recv_cloud = False
        self.retrive_version = {}

    def prepare(self):
        """
        测试串口是否能正常打开
        :return:
        """
        try:
            self.ser = serial.Serial(self.com, self.baud, timeout=0)
        except Exception as e:
            self.ser = None
            logger.error(e)
            return False
        return True

    def destroy(self):
        """
        销毁串口对象
        :return:
        """
        if self.ser is not None:
            self.ser.close()

    def get_version(self, device_id):
        self.ser.flushInput()
        self.send_msg(device_id, 1, 0x12)
        response, all_recv = self.get_response(1)
        # logger.debug('get ver %s' % str(device_id))
        if len(all_recv) > 0:
            # logger.debug('ver response %s' % str(device_id))
            smokesignal.emit('data_signal',str(device_id), all_recv)

    def rcv_version(self, desc, device_id, version):
        self.retrive_version[desc] = False

    def run(self):
        frame_id = 0
        # 先获取一次版本号
        for device_id in self.ids_485:
            self.get_version(device_id)
        # 主循环
        while self.is_run:
            if not self.is_pause:
                try:
                    # 发送cfg配置
                    self.send_cfg()
                    # 更新固件
                    self.update_firmware()
                    for device_id in [id for id in self.retrive_version.keys() if self.retrive_version[id] is True]:
                        self.get_version(int(device_id))
                    # 接收数据
                    frame_id += 1
                    if self.query_normal:
                        for device_id in self.ids_485:
                            self.ser.flushInput()
                            self.send_msg(device_id, frame_id, 0x15 if self.is_debug else 0x02)
                            # 这里逻辑较为复杂，不能等待超时（轮询时间过长），又要完整接收到雷达响应，因此需要解析包头
                            response, all_recv = self.get_response(0.2)
                            if len(all_recv) > 0:
                                smokesignal.emit('data_signal',str(device_id), all_recv)
                    if self.recv_cloud:
                        response, all_recv = self.get_response(0.2)
                        if len(all_recv) > 0:
                            smokesignal.emit('data_signal',str(device_id), all_recv)
                    # 用户控制发送
                    while not self.to_send_queue.empty():
                        msg = self.to_send_queue.get()
                        for device_id in self.ids_485:
                            self.ser.flushInput()
                            self.send_msg(device_id, frame_id, msg[0], msg[1], msg[2])
                            response, all_recv = self.get_response(0.2)
                            if len(all_recv) > 0:
                                smokesignal.emit('data_signal',str(device_id), all_recv)
                except Exception as e:
                    logger.error(e)
            self.msleep(10)

    def add_msg(self, _cmd_id, _msg_len=0x0c, _data=None):
        self.to_send_queue.put((_cmd_id, _msg_len, _data))

    def send_msg(self, _device_id, _frame_id, _cmd_id=2, _msg_len=0x0c, _data=None):
        time.sleep(0.01)
        buf = bytes()
        # 前导码
        buf += b'\xff\xff\xff\xff'[::-1]
        #
        buf_back = bytes()
        # 协议代码
        buf_back += b'\xc1\x02'[::-1]
        # 数据长度
        buf_back += struct.pack('<H', _msg_len)
        # 消息数据
        #  校验码
        buf_back += b'\x00\x00'[::-1]
        #  帧选项
        buf_back += b'\x40'[::-1]
        #  命令代码
        buf_back += struct.pack('<B', _cmd_id)
        #  设备地址
        buf_back += struct.pack('<H', _device_id)
        #  帧序号
        _frame_id %= 0xffff
        buf_back += struct.pack('<H', _frame_id)
        #  时间
        buf_back += struct.pack('<I', 0)
        # body
        if _data is not None:
            buf_back += _data
        # 校验码
        checksum = Crc.calc(buf_back)
        buf += struct.pack("<H", checksum)
        buf += buf_back
        # send
        ###############
        print("send: ", end=" ")
        for b in buf:
            print("%02X" % b, end=" ")
        print("")
        try:
            self.ser.write(buf)
        except Exception as e:
            print(e)

    def send_cfg(self):
        if self.cfg_cmds is not None:
            str_cmds = self.cfg_cmds
            self.cfg_cmds = None
            self.retrive_version.clear()
            cmds = str_cmds.split("\n")
            # filter
            ids_485 = self.ids_485
            if self.cfg_filter is not None:
                cfg_filter_segs = self.cfg_filter.split(";")
                ids_485 = [x for x in self.ids_485 if str(x) in cfg_filter_segs]
            smokesignal.emit('cfg_result_signal',"", ";".join([str(x) for x in ids_485]))
            for device_id in ids_485:
                frame_id = 0
                ret_desc = ""
                cur_cmd_idx = 1
                for cmd in cmds:
                    frame_id += 1
                    self.ser.flushInput()
                    cmd_byte = bytes(cmd + "\n", "utf-8")
                    self.send_msg(device_id, frame_id, 0x10, 0x0c + len(cmd_byte), cmd_byte)
                    response = self.get_ota_response(1)
                    if response is None:
                        ret_desc += cmd + " : no data received\r\n"
                    elif response[1] != 0x01:
                        ret_desc += cmd + " : %02X" % response[1] + "\r\n"
                    smokesignal.emit('cfg_result_signal',str(device_id), int(cur_cmd_idx * 100 / len(cmds)))
                    cur_cmd_idx += 1
                smokesignal.emit('cfg_result_signal',str(device_id), ret_desc)
                self.retrive_version[str(device_id)] = True

    def update_firmware(self):
        if self.firmware_path is not None:
            file_path = self.firmware_path
            self.firmware_path = None
            self.retrive_version.clear()
            # filter
            ids_485 = self.ids_485
            if self.firmware_filter is not None:
                firmware_filter_segs = self.firmware_filter.split(";")
                ids_485 = [x for x in self.ids_485 if str(x) in firmware_filter_segs]
            smokesignal.emit('firm_result_signal',"", ";".join([str(x) for x in ids_485]))
            for device_id in ids_485:
                ret_desc = ""
                # 1. 发送ReadyUpdate
                ret = False
                cmd = bytes("ReadyUpdate\n", "utf-8")
                for i in range(5):
                    self.ser.flushInput()
                    self.send_msg(device_id, 1, 0x10, 0x0c + len(cmd), cmd)
                    ret = self.get_exact_ota_response(b'\xAA\x21\xCB\x55', 1)
                    if ret:
                        break
                if not ret:
                    ret_desc = self.tr("ReadyUpdate命令未收到响应")
                else:
                    smokesignal.emit('firm_progress_signal',str(device_id), 10)
                    # 2. 发送Update
                    cmd = bytes("Update\n", "utf-8")
                    self.send_msg(device_id, 1, 0x10, 0x0c + len(cmd), cmd)
                    if not self.get_exact_ota_response(b'\xAA\x22\xCC\x55', 20):
                        ret_desc = self.tr("Update命令未收到响应")
                    else:
                        smokesignal.emit('firm_progress_signal',str(device_id), 20)
                        # 3. XModem协议传输文件
                        file = open(file_path, "rb")
                        file_size = os.path.getsize(file_path)
                        packet_size = math.ceil(file_size / 1024)

                        def getc(size, timeout=1):
                            data_recv = None
                            try:
                                package_len = 18 + size
                                # 先找包头 FFFFFFFF
                                idx = 0
                                start_time = time.time()
                                buf = bytes()
                                while True:
                                    if time.time() - start_time > timeout:
                                        break
                                    data = self.ser.read(1)
                                    if data is not None and len(data) > 0:
                                        if idx < 4:
                                            if data[0] == 0xFF:
                                                idx += 1
                                            else:
                                                idx = 0
                                            if idx == 4:
                                                buf = b'\xFF\xFF\xFF\xFF'
                                        elif idx < package_len:
                                            buf += data
                                            idx += 1
                                            if idx == package_len:
                                                # print("getc:", end=" ")
                                                # for b in buf:
                                                #     print("%02X" % b, end=" ")
                                                # print("")
                                                data_recv = self.decode_bag(buf)[0]
                                                break
                            except Exception as err:
                                logger.error(err)
                            return data_recv

                        def putc(data, timeout=1):
                            # print("putc:", end=" ")
                            time.sleep(0.005)
                            return self.send_msg(device_id, 1, 0x11, 0x0c + len(data), data)

                        def callback_func(total_packets, success_count, error_count):
                            smokesignal.emit('firm_progress_signal',str(device_id), 20 + int(success_count * 70 / packet_size))

                        xmodem = XMODEM(getc, putc, mode='xmodem1k')
                        xmodem_ret = xmodem.send(file, callback=callback_func)
                        file.close()
                        if not xmodem_ret:
                            ret_desc = self.tr("XModem传输错误")
                        else:
                            # 4. 确认响应
                            if not self.get_exact_ota_response(b'\xAA\x23\xCD\x55', 15):
                                ret_desc = self.tr("未收到固件更新完成响应")
                            else:
                                smokesignal.emit('firm_progress_signal',str(device_id), 100)
                                self.retrive_version[str(device_id)] = True
                smokesignal.emit('firm_result_signal',str(device_id), ret_desc)

    def decode_bag(self, bag):
        if len(bag) > 10:
            for i in range(0, len(bag) - 10):
                if bag[i] == 0xFF and bag[i + 1] == 0xFF and \
                                bag[i + 2] == 0xFF and bag[i + 3] == 0xFF:
                    bag = bag[i:]
                    # 校验码
                    checksum = struct.unpack('<H', bag[4: 6])[0]
                    # 协议代码
                    protocol = struct.unpack('<H', bag[6: 8])[0]
                    # 数据长度
                    msg_len = struct.unpack('<H', bag[8: 10])[0]
                    if len(bag) >= (10 + msg_len):
                        calc_checksum = Crc.calc(bag[6: 10 + msg_len])
                        if checksum == calc_checksum:
                            # 消息数据
                            msg_checksum = struct.unpack('<H', bag[10: 12])[0]
                            msg_frame = struct.unpack('<B', bag[12: 13])[0]
                            msg_cmd = struct.unpack('<B', bag[13: 14])[0]
                            msg_device_id = struct.unpack('<H', bag[14: 16])[0]
                            msg_frame_id = struct.unpack('<H', bag[16: 18])[0]
                            # 判断消息类型
                            if msg_cmd == 0x10:
                                return bag[18: 22], bag[10 + msg_len:]
                            elif msg_cmd == 0x11:
                                return bag[18: 18 + msg_len - 8], bag[10 + msg_len:]
                            else:
                                return None, bag[10 + msg_len:]
                        else:
                            for j in range(0, 10 + msg_len):
                                print("%02X" % bag[j], end=" ")
                            print("")
                            print("checksum err %X %X" % (checksum, calc_checksum))
                    return None, bag
        return None, bag

    def get_response(self, timeout):
        idx = 0
        all_recv = bytes()
        response = bytes()
        msg_len = -1
        start_time = time.time()
        while True:
            try:
                if time.time() - start_time > timeout:
                    break
                data = self.ser.read(1)
                if data is None or len(data) == 0:
                    continue
                all_recv += data
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
            except Exception as e:
                logger.error(e)
        if msg_len != -1 and len(response) == (10 + msg_len):
            return response, all_recv
        else:
            return None, all_recv

    def get_ota_response(self, timeout):
        idx = 0
        response = bytes()
        msg_len = -1
        start_time = time.time()
        print("recv:")
        while True:
            try:
                if time.time() - start_time > timeout:
                    break
                data = self.ser.read(1)
                if data is None or len(data) == 0:
                    continue
                print("%02X " % data[0], end="")
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
                        # 需要确认命令码，ota应答为0x10
                        msg_cmd = struct.unpack('<B', response[13: 14])[0]
                        if msg_cmd == 0x10:
                            break
                        else:
                            idx = 0
                            response = bytes()
                            msg_len = -1
            except Exception as e:
                logger.error(e)
        print("")
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
