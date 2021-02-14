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


class MsgJZQ(object):

    HEADER_JZQ = b'\x55\xAA'
    TAIL_JZQ = b'\xAA\x55'

    def __init__(self):
        #
        self.header = MsgJZQ.HEADER_JZQ
        self.tail = MsgJZQ.TAIL_JZQ
        # 线路编号
        self.id_line = 0
        # 数据长度
        self.data_len = 0
        # 数据内容
        self.data = bytes()
        # 校验码
        self.checksum = 0

    def set_data(self, data):
        self.data = data
        self.data_len = len(data)


class MsgJZQSend(MsgJZQ):

    def __init__(self, id_line):
        super(MsgJZQSend, self).__init__()
        self.id_line = id_line

    def get_bytes(self):
        buf = bytes()
        #
        buf += self.header
        #
        buf_back = bytes()
        #
        buf_back += struct.pack('<B', self.id_line)
        #
        buf_back += struct.pack('<H', self.data_len)
        #
        buf_back += self.data
        #
        checksum = Crc.calc(buf_back)
        #
        buf += buf_back
        buf += struct.pack("<H", checksum)
        #
        buf += self.tail
        #
        return buf


class MsgJZQRecv(MsgJZQ):

    def __init__(self):
        super(MsgJZQRecv, self).__init__()

    @staticmethod
    def parse_data(data):
        cache = data
        # 参考 《博瑞康木牛对接文档v1.02》
        msgs = []
        while True:
            header_pos = cache.find(MsgJZQ.HEADER_JZQ)
            if header_pos > -1:
                # 找到包头，删除包头前面的数据
                cache = cache[header_pos:]
                #
                if len(cache) >= 5:
                    # 数据长度
                    data_len = struct.unpack('<H', cache[3: 5])[0]
                    if data_len > 1400:
                        # 异常包，正常一包数据长度不会超过1M
                        cache = cache[5:]
                        continue
                    else:
                        if len(cache) >= (9 + data_len):
                            checksum = struct.unpack('<H', cache[5 + data_len: 7 + data_len])[0]
                            calc_checksum = Crc.calc(cache[2: 5 + data_len])
                            if checksum == calc_checksum and cache[7 + data_len: 9 + data_len] == MsgJZQ.TAIL_JZQ:
                                msg = MsgJZQRecv()
                                # 线路编号
                                msg.id_line = struct.unpack('<B', cache[2: 3])[0]
                                msg.data_len = data_len
                                msg.data = cache[5: 5 + data_len]
                                msg.checksum = checksum
                                msgs.append(msg)
                                cache = cache[9 + data_len:]
                                continue
                            else:
                                # 异常包，校验不通过
                                cache = cache[5:]
                                continue
                        else:
                            break
                else:
                    break
            else:
                # 未找到包头，异常数据，直接清空
                cache = bytes()
                break
        return cache, msgs
