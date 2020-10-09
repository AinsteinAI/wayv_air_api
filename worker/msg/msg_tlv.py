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
from worker.msg.msg_detail import *


class MsgTlv(object):

    HEADER_TLV = b'\x02\x01\x04\x03\x06\x05\x08\x07'

    def __init__(self):
        # 包头
        self.header = MsgTlv.HEADER_TLV
        self.version = 0
        self.platform = 0
        self.timestamp = 0
        self.packet_length = 0
        self.frame_number = 0
        self.sub_frame_number = 0
        self.chirp_margin = 0
        self.frame_margin = 0
        self.uart_sent_time = 0
        self.track_process_time = 0
        self.num_tlv = 0
        self.checksum = 0
        self.tlvs = []

    @staticmethod
    def parse_data(data):
        # 参考 《Overhead_People_Tracking_and_Stance_Detection_users_guide》
        cache = data
        msgs = []
        while True:
            header_pos = cache.find(MsgTlv.HEADER_TLV)
            if header_pos > -1:
                # 找到包头，删除包头前面的数据
                cache = cache[header_pos:]
                #
                if len(cache) >= 52:
                    if not MsgTlv.valid_check(cache[0: 52]):
                        print("tlv head check err")
                        cache = cache[len(MsgTlv.HEADER_TLV):]
                    else:
                        packet_len = struct.unpack('<I', cache[20: 24])[0]
                        if len(cache) >= packet_len:
                            msg = MsgTlv()
                            msg.header = cache[0: 8]
                            msg.version = struct.unpack('<I', cache[8: 12])[0]
                            msg.platform = struct.unpack('<I', cache[12: 16])[0]
                            msg.timestamp = struct.unpack('<I', cache[16: 20])[0]
                            msg.packet_length = packet_len
                            msg.frame_number = struct.unpack('<I', cache[24: 28])[0]
                            msg.sub_frame_number = struct.unpack('<I', cache[28: 32])[0]
                            msg.chirp_margin = struct.unpack('<I', cache[32: 36])[0]
                            msg.frame_margin = struct.unpack('<I', cache[36: 40])[0]
                            msg.uart_sent_time = struct.unpack('<I', cache[40: 44])[0]
                            msg.track_process_time = struct.unpack('<I', cache[44: 48])[0]
                            msg.num_tlv = struct.unpack('<H', cache[48: 50])[0]
                            msg.checksum = struct.unpack('<H', cache[50: 52])[0]
                            #
                            start = 52
                            tlv_len_sum = 0
                            for i in range(msg.num_tlv):
                                tlv_type = struct.unpack('<I', cache[start: start + 4])[0]
                                tlv_len = struct.unpack('<I', cache[start + 4: start + 8])[0]
                                if start + tlv_len > packet_len:
                                    break
                                tlv_len_sum += tlv_len
                                # print("tlv_len: %d tlv_type：%d" % (tlv_len, tlv_type))
                                if tlv_type == 6:
                                    tlv = MsgPointCloud.parse_data(cache[start: start + tlv_len])
                                    msg.tlvs.append(tlv)
                                elif tlv_type == 7:
                                    tlv = MsgTargetObject.parse_data(cache[start: start + tlv_len])
                                    msg.tlvs.append(tlv)
                                elif tlv_type == 8:
                                    tlv = MsgTargetIndex.parse_data(cache[start: start + tlv_len])
                                    msg.tlvs.append(tlv)
                                start += tlv_len
                            # check
                            if 52 + tlv_len_sum == msg.packet_length:
                                msgs.append(msg)
                                cache = cache[packet_len:]
                            else:
                                print("tlv body check err")
                                cache = cache[len(MsgTlv.HEADER_TLV):]
                            continue
                        else:
                            break
                else:
                    break
            else:
                # 未找到包头，不能直接清空，保留包头长度-1
                if len(cache) >= len(MsgTlv.HEADER_TLV):
                    cache = cache[-len(MsgTlv.HEADER_TLV) + 1: len(cache)]
                break
        return cache, msgs

    @staticmethod
    def valid_check(tlv_head):
        h_list = list(struct.unpack('<26H', tlv_head))
        h_sum = sum(h_list)
        bs = struct.pack('<I', h_sum)
        h_list = list(struct.unpack('<2H', bs))
        h_sum = sum(h_list)
        bs = struct.pack('<I', h_sum)
        b = struct.unpack('<H', bs[0: 2])[0]
        return b == 0xFFFF
