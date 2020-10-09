# -*- coding: utf-8 -*-
'''
Copyright 2020, Ainstein Inc. All Rights Reserved


 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 '''
import struct
from crc import Crc


class Msg485(object):

    HEADER_485 = b'\xFF\xFF\xFF\xFF'

    def __init__(self):
        # 前导码
        self.header = Msg485.HEADER_485
        # 校验码
        self.checksum = 0
        # 协议代码
        self.protocol_code = 0xc102
        # 数据长度
        self.data_len = 0

        # 校验码(暂时无效)
        self.checksum2 = 0
        # 帧选项
        self.frame_option = 0
        # 命令代码
        self.cmd_code = 0
        # 485id
        self.id_485 = 0
        # 帧序号
        self.frame_idx = 0
        # 帧内容
        self.frame_data = bytes()


class Msg485Send(Msg485):

    def __init__(self, id_485, frame_idx=0):
        super(Msg485Send, self).__init__()
        # unix时间
        self.unix_time = 0
        #
        self.frame_option = 0x40
        #
        self.id_485 = id_485
        #
        self.frame_idx = frame_idx

    def get_bytes(self):
        buf = bytes()
        # 前导码
        buf += self.header[::-1]
        #
        buf_back = bytes()
        # 协议代码
        buf_back += struct.pack('<H', self.protocol_code)
        # 数据长度
        buf_back += struct.pack('<H', 12 + len(self.frame_data))
        #  校验码
        buf_back += struct.pack('<H', self.checksum2)
        #  帧选项
        buf_back += struct.pack('<B', self.frame_option)
        #  命令代码
        buf_back += struct.pack('<B', self.cmd_code)
        #  设备地址
        buf_back += struct.pack('<H', self.id_485)
        #  帧序号
        buf_back += struct.pack('<H', self.frame_idx)
        #  时间
        buf_back += struct.pack('<I', self.unix_time)
        # body
        buf_back += self.frame_data
        # 校验码
        checksum = Crc.calc(buf_back)
        buf += struct.pack("<H", checksum)
        buf += buf_back
        #
        return buf

    def get_cmd(self, cmd_code, frame_data):
        self.cmd_code = cmd_code
        self.frame_data = frame_data
        self.data_len = 12 + len(frame_data)
        return self.get_bytes()


class Msg485Recv(Msg485):

    def __init__(self):
        super(Msg485Recv, self).__init__()
        #
        self.frame_option = 0xc0

    def is_msg(self, cmd_code):
        return self.cmd_code == cmd_code

    @staticmethod
    def parse_data(data):
        # 参考 《VAVE之485协议定义V1.07》
        cache = data
        msgs = []
        while True:
            header_pos = cache.find(Msg485.HEADER_485)
            if header_pos > -1:
                # 找到包头，删除包头前面的数据
                cache = cache[header_pos:]
                #
                if len(cache) >= 10:
                    # 校验码
                    checksum = struct.unpack('<H', cache[4: 6])[0]
                    # 协议代码
                    protocol_code = struct.unpack('<H', cache[6: 8])[0]
                    # 数据长度
                    data_len = struct.unpack('<H', cache[8: 10])[0]
                    if data_len > 1024:
                        # 异常包，正常一包数据长度不会超过1k
                        cache = cache[10:]
                        continue
                    else:
                        if len(cache) >= (10 + data_len):
                            calc_checksum = Crc.calc(cache[6: 10 + data_len])
                            if checksum == calc_checksum:
                                msg = Msg485Recv()
                                msg.checksum = checksum
                                msg.protocol_code = protocol_code
                                msg.data_len = data_len
                                # 消息数据
                                msg.checksum2 = struct.unpack('<H', cache[10: 12])[0]
                                # 帧选项
                                msg.frame_option = struct.unpack('<B', cache[12: 13])[0]
                                # 命令代码
                                msg.cmd_code = struct.unpack('<B', cache[13: 14])[0]
                                # 设备地址
                                msg.id_485 = struct.unpack('<H', cache[14: 16])[0]
                                # 帧序号
                                msg.frame_idx = struct.unpack('<H', cache[16: 18])[0]
                                # 帧内容
                                msg.frame_data = cache[18: 10 + data_len]
                                msgs.append(msg)
                                cache = cache[10 + data_len:]
                                continue
                            else:
                                # 异常包，校验不通过
                                cache = cache[10:]
                                continue
                        else:
                            break
                else:
                    break
            else:
                # 未找到包头，不能直接清空，保留包头长度-1
                if len(cache) >= len(Msg485.HEADER_485):
                    cache = cache[-len(Msg485.HEADER_485) + 1: len(cache)]
                break
        return cache, msgs
