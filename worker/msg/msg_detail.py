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
import struct
from model.target import Target, DebugTarget, DetailTarget, TLVCloudPoint, TLVTargetPoint, TLVTargrtIndex

CMD_485_VERSION = 0x12
CMD_485_TARGET = 0x02
CMD_485_DEBUG_TARGET = 0x15
CMD_485_OTA = 0x10
CMD_485_OTA_XMODEM = 0x11
CMD_485_PRODUCTION_TARGET = 0x13
CMD_485_CONFIG = 0x14
CMD_485_PARAM = 0x16
CMD_485_SBL = 0x17
CMD_485_DETAIL_TARGET=0x18


class MsgDetail(object):
    @staticmethod
    def parse_data(cmd_code, data):
        if cmd_code == CMD_485_VERSION:
            return MsgVersion.parse_data(data)
        elif cmd_code == CMD_485_TARGET:
            return MsgTarget.parse_data(data)
        elif cmd_code == CMD_485_DEBUG_TARGET:
            return MsgDebugTarget.parse_data(data)
        elif cmd_code == CMD_485_DETAIL_TARGET:
            return MsgDetailTarget.parse_data(data)
        elif cmd_code == CMD_485_OTA or cmd_code == CMD_485_SBL:
            return MsgOta.parse_data(data)
        elif cmd_code == CMD_485_OTA_XMODEM:
            return MsgOtaXmodem.parse_data(data)
        elif cmd_code == CMD_485_CONFIG:
            return MsgConfig.parse_data(data)
        elif cmd_code == CMD_485_PARAM:
            return MsgParam.parse_data(data)
        return None


class Version(object):
    def __init__(self):
        # 版本名称
        self.soft_name = ""
        # 主版本号
        self.ver_main = 0
        # 子版本号
        self.ver_child = 0
        # 阶段版本号
        self.ver_sec = 0
        # 年月日
        self.year = 0
        self.month = 0
        self.day = 0


class MsgVersion(object):
    def __init__(self):
        # 设备id
        self.device_id = ""
        # 软件数量
        self.soft_count = 0
        # 版本号长度
        self.ver_len = 0xc102
        #
        self.versions = []

    def __str__(self):
        out_text = ""
        for version in self.versions:
            out_text += "%s:v%d.%d.%d " % (version.soft_name, version.ver_main, version.ver_child, version.ver_sec)
        return out_text

    @staticmethod
    def parse_data(data):
        cache = data
        msg = MsgVersion()
        # 设备id
        device_id = cache[0: 16]
        msg.device_id = "".join([chr(x) for x in device_id])
        # 软件数量
        msg.soft_count = struct.unpack('<B', cache[16: 17])[0]
        # 版本号长度
        msg.ver_len = struct.unpack('<B', cache[17: 18])[0]
        #
        cache = cache[18:]
        for j in range(0, msg.soft_count):
            version = Version()
            soft_num = struct.unpack('<B', cache[0: 1])[0]
            if soft_num == 1:
                version.soft_name = "Firmware"
            elif soft_num == 3:
                version.soft_name = "SBL"
            version.ver_main = struct.unpack('<B', cache[1: 2])[0]
            version.ver_child = struct.unpack('<B', cache[2: 3])[0]
            version.ver_sec = struct.unpack('<B', cache[3: 4])[0]
            version.year = struct.unpack('<B', cache[4: 5])[0]
            version.month = struct.unpack('<B', cache[5: 6])[0]
            version.day = struct.unpack('<B', cache[6: 7])[0]
            msg.versions.append(version)
            cache = cache[msg.ver_len:]
        return msg


class Tag(object):
    def __init__(self):
        # 设备类型
        self.device_type = 0
        # 设备温度
        self.temp = 0
        # 设备电压
        self.vol = 0
        # 设备功率
        self.power = 0
        # TX1 TX2 TX3 温度
        self.tem_tx1 = 0
        self.tem_tx2 = 0
        self.tem_tx3 = 0
        # pm温度
        self.tem_pm = 0
        # 告警码
        self.warning_code = 0
        # 目标数量
        self.target_count = 0
        # 目标数据长度
        self.target_size = 0
        #
        self.targets = []

    def __str__(self):
        out_text = "Target num:%d Temperature:%.1f℃  Voltage:%.1fV Power:%.1fW TX1 Temperature:%d TX2 " \
                "Temperature:%d TX3 Temperature:%d PM Temperature:%d " % (len(self.targets), self.temp,
                                                                            self.vol / 1000, self.power / 1000,
                                                                            self.tem_tx1, self.tem_tx2,
                                                                            self.tem_tx3, self.tem_pm)
        return out_text


class MsgTarget(object):
    def __init__(self):
        # 标签总数
        self.tag_count = 0
        #
        self.tags = []

    @staticmethod
    def parse_data(data):
        cache = data
        msg = MsgTarget()
        msg.tag_count = struct.unpack('<B', cache[0: 1])[0]
        cache = cache[1:]
        for i in range(0, msg.tag_count):
            tag = Tag()
            msg.tags.append(tag)
            # 设备类型
            tag.device_type = struct.unpack('<B', cache[0: 1])[0]
            # 设备温度
            tag.temp = struct.unpack('<f', cache[1: 5])[0]
            # 设备电压
            tag.vol = struct.unpack('<f', cache[5: 9])[0]
            # 设备功率
            tag.power = struct.unpack('<f', cache[9: 13])[0]
            # tx1 温度
            tag.tem_tx1 = struct.unpack('<h', cache[13: 15])[0]
            # tx2 温度
            tag.tem_tx2 = struct.unpack('<h', cache[15: 17])[0]
            # tx3 温度
            tag.tem_tx3 = struct.unpack('<h', cache[17: 19])[0]
            # pm 温度
            tag.tem_pm = struct.unpack('<h', cache[19: 21])[0]
            # 告警码
            tag.warning_code = struct.unpack('<B', cache[21: 22])[0]
            # 目标个数
            tag.target_count = struct.unpack('<B', cache[22: 23])[0]
            #
            tag.target_size = struct.unpack('<B', cache[23: 24])[0]
            #
            cache = cache[24:]
            for j in range(0, tag.target_count):
                target = Target()
                tag.targets.append(target)
                target.tid = struct.unpack('<B', cache[0: 1])[0]
                target.x = struct.unpack('<f', cache[1: 5])[0]
                target.y = struct.unpack('<f', cache[5: 9])[0]
                target.z = struct.unpack('<f', cache[9: 13])[0]
                cache = cache[tag.target_size:]
        return msg


class MsgDebugTarget(object):
    def __init__(self):
        # 标签总数
        self.tag_count = 0
        #
        self.tags = []

    @staticmethod
    def parse_data(data):
        try:
            cache = data
            msg = MsgDebugTarget()
            msg.tag_count = struct.unpack('<B', cache[0: 1])[0]
            cache = cache[1:]
            for i in range(0, msg.tag_count):
                tag = Tag()
                msg.tags.append(tag)
                # 设备类型
                tag.device_type = struct.unpack('<B', cache[0: 1])[0]
                # 设备温度
                tag.temp = struct.unpack('<f', cache[1: 5])[0]
                # 设备电压
                tag.vol = struct.unpack('<f', cache[5: 9])[0]
                # 设备功率
                tag.power = struct.unpack('<f', cache[9: 13])[0]
                # tx1 温度
                tag.tem_tx1 = struct.unpack('<h', cache[13: 15])[0]
                # tx2 温度
                tag.tem_tx2 = struct.unpack('<h', cache[15: 17])[0]
                # tx3 温度
                tag.tem_tx3 = struct.unpack('<h', cache[17: 19])[0]
                # pm 温度
                tag.tem_pm = struct.unpack('<h', cache[19: 21])[0]
                # 告警码
                tag.warning_code = struct.unpack('<B', cache[21: 22])[0]
                # 目标个数
                tag.target_count = struct.unpack('<B', cache[22: 23])[0]
                #
                tag.target_size = struct.unpack('<B', cache[23: 24])[0]
                #
                cache = cache[24:]
                for j in range(0, tag.target_count):
                    target = DebugTarget()
                    tag.targets.append(target)
                    target.tid = struct.unpack('<B', cache[0: 1])[0]
                    target.x = struct.unpack('<f', cache[1: 5])[0]
                    target.y = struct.unpack('<f', cache[5: 9])[0]
                    target.z = struct.unpack('<f', cache[9: 13])[0]
                    target.vel_x = struct.unpack('<f', cache[13: 17])[0]
                    target.vel_y = struct.unpack('<f', cache[17: 21])[0]
                    target.vel_z = struct.unpack('<f', cache[21: 25])[0]
                    target.a_x = struct.unpack('<f', cache[25: 29])[0]
                    target.a_y = struct.unpack('<f', cache[29: 33])[0]
                    target.a_z = struct.unpack('<f', cache[33: 37])[0]
                    target.cp_count = struct.unpack('<H', cache[37: 39])[0]
                    target.is_target_static = struct.unpack('<H', cache[39: 41])[0]
                    target.thre = struct.unpack('<H', cache[41: 43])[0]
                    target.active2_free_count = struct.unpack('<H', cache[43: 45])[0]
                    cache = cache[tag.target_size:]
        except:
            pass
        return msg

class MsgDetailTarget(object):
    def __init__(self):
        # 标签总数
        self.tag_count = 0
        #
        self.tags = []

    @staticmethod
    def parse_data(data):
        try:
            cache = data
            msg = MsgDetailTarget()
            msg.tag_count = struct.unpack('<B', cache[0: 1])[0]
            cache = cache[1:]
            for i in range(0, msg.tag_count):
                tag = Tag()
                msg.tags.append(tag)
                # 设备类型
                tag.device_type = struct.unpack('<B', cache[0: 1])[0]
                # 设备温度
                tag.temp = struct.unpack('<f', cache[1: 5])[0]
                # 设备电压
                tag.vol = struct.unpack('<f', cache[5: 9])[0]
                # 设备功率
                tag.power = struct.unpack('<f', cache[9: 13])[0]
                # tx1 温度
                tag.tem_tx1 = struct.unpack('<h', cache[13: 15])[0]
                # tx2 温度
                tag.tem_tx2 = struct.unpack('<h', cache[15: 17])[0]
                # tx3 温度
                tag.tem_tx3 = struct.unpack('<h', cache[17: 19])[0]
                # pm 温度
                tag.tem_pm = struct.unpack('<h', cache[19: 21])[0]
                # 告警码
                tag.warning_code = struct.unpack('<B', cache[21: 22])[0]
                # 目标个数
                tag.target_count = struct.unpack('<B', cache[22: 23])[0]
                #
                tag.target_size = struct.unpack('<B', cache[23: 24])[0]
                #
                cache = cache[24:]
                for j in range(0, tag.target_count):
                    target = DetailTarget()
                    tag.targets.append(target)
                    target.tid = struct.unpack('<B', cache[0: 1])[0]
                    target.x = struct.unpack('<f', cache[1: 5])[0]
                    target.y = struct.unpack('<f', cache[5: 9])[0]
                    target.z = struct.unpack('<f', cache[9: 13])[0]
                    target.vel_x = struct.unpack('<f', cache[13: 17])[0]
                    target.vel_y = struct.unpack('<f', cache[17: 21])[0]
                    target.vel_z = struct.unpack('<f', cache[21: 25])[0]
                    target.a_x = struct.unpack('<f', cache[25: 29])[0]
                    target.a_y = struct.unpack('<f', cache[29: 33])[0]
                    target.a_z = struct.unpack('<f', cache[33: 37])[0]
                    target.cp_count = struct.unpack('<H', cache[37: 39])[0]
                    cache = cache[tag.target_size:]
        except:
            pass
        return msg


class MsgOta(object):
    def __init__(self):
        # 响应
        self.response = 0
        #
        self.crc = 0

    @staticmethod
    def parse_data(data):
        cache = data
        msg = MsgOta()
        msg.response = struct.unpack('<B', cache[1: 2])[0]
        msg.crc = struct.unpack('<B', cache[2: 3])[0]
        return msg


class MsgOtaXmodem(object):
    def __init__(self):
        self.data = bytes()

    @staticmethod
    def parse_data(data):
        msg = MsgOtaXmodem()
        msg.data = data
        return msg


class MsgPointCloud(object):
    def __init__(self):
        self.point_clouds = []

    @staticmethod
    def parse_data(data):
        msg = MsgPointCloud()
        tlv_type = struct.unpack('<I', data[0: 4])[0]
        tlv_len = struct.unpack('<I', data[4: 8])[0]
        for j in range(8, tlv_len, 20):
            p_range = struct.unpack('<f', data[j: j + 4])[0]
            p_azimuth = struct.unpack('<f', data[j + 4: j + 8])[0]
            p_elevation = struct.unpack('<f', data[j + 8: j + 12])[0]
            p_doppler = struct.unpack('<f', data[j + 12: j + 16])[0]
            p_snr = struct.unpack('<f', data[j + 16: j + 20])[0]
            cp = TLVCloudPoint(p_range, p_azimuth, p_elevation, p_doppler, p_snr)
            msg.point_clouds.append(cp)
        return msg


class MsgTargetObject(object):
    def __init__(self):
        self.target_objects = []

    @staticmethod
    def parse_data(data):
        msg = MsgTargetObject()
        tlv_type = struct.unpack('<I', data[0: 4])[0]
        tlv_len = struct.unpack('<I', data[4: 8])[0]
        for i in range(8, tlv_len, 48):
            t_tid = struct.unpack('<i', data[i: i + 4])[0]
            t_pos_x = struct.unpack('<f', data[i + 4: i + 8])[0]
            t_pos_y = struct.unpack('<f', data[i + 8: i + 12])[0]
            t_pos_z = struct.unpack('<f', data[i + 12: i + 16])[0]
            t_vel_x = struct.unpack('<f', data[i + 16: i + 20])[0]
            t_vel_y = struct.unpack('<f', data[i + 20: i + 24])[0]
            t_vel_z = struct.unpack('<f', data[i + 24: i + 28])[0]
            t_dim_x = struct.unpack('<f', data[i + 28: i + 32])[0]
            t_dim_y = struct.unpack('<f', data[i + 32: i + 36])[0]
            t_dim_z = struct.unpack('<f', data[i + 36: i + 40])[0]
            cp_count = struct.unpack("<H", data[i + 40: i + 42])[0]
            is_target_static = struct.unpack("<H", data[i + 42: i + 44])[0]
            thre = struct.unpack('<H', data[i + 44: i + 46])[0]
            active2_free_count = struct.unpack('<H', data[i + 46: i + 48])[0]
            to = TLVTargetPoint(t_tid, t_pos_x, t_pos_y, t_pos_z, t_vel_x, t_vel_y, t_vel_z,
                                t_dim_x, t_dim_y, t_dim_z, cp_count, is_target_static, thre, active2_free_count)
            msg.target_objects.append(to)
        return msg


class MsgTargetIndex(object):
    def __init__(self):
        self.target_indexs = []

    @staticmethod
    def parse_data(data):
        msg = MsgTargetIndex()
        tlv_type = struct.unpack('<I', data[0: 4])[0]
        tlv_len = struct.unpack('<I', data[4: 8])[0]
        for j in range(8, tlv_len, 1):
            index = struct.unpack('<B', data[j: j + 1])[0]
            ti = TLVTargrtIndex(index)
            msg.target_indexs.append(ti)
        return msg


class MsgConfig(object):
    def __init__(self):
        self.id_485 = 0
        self.baud_485 = 0
        self.server_ip = ""
        self.server_port = 0
        self.wifi_name = ""
        self.wifi_pwd = ""
        self.con_wifi_name = ""
        self.con_wifi_pwd = ""
        self.dev_id = ""
        self.wifi_mode = 0
        self.sys_mode = 0
        self.radio_switch = 0
        self.radio_time = 0

    @staticmethod
    def parse_data(data):
        chr_0 = chr(0)
        msg = MsgConfig()
        msg.id_485 = struct.unpack('<H', data[0: 2])[0]
        msg.baud_485 = struct.unpack('<I', data[2: 6])[0]
        msg.server_port = struct.unpack('<I', data[6: 10])[0]
        msg.server_ip = data[10: 30].decode("utf-8").strip(chr_0)
        msg.wifi_name = data[30: 62].decode("utf-8").strip(chr_0)
        msg.wifi_pwd = data[62: 78].decode("utf-8").strip(chr_0)
        msg.con_wifi_name = data[78: 110].decode("utf-8").strip(chr_0)
        msg.con_wifi_pwd = data[110: 126].decode("utf-8").strip(chr_0)
        msg.dev_id = data[126: 142].decode("utf-8").strip(chr_0)
        msg.wifi_mode = struct.unpack('<B', data[142: 143])[0]
        msg.sys_mode = struct.unpack('<B', data[143: 144])[0]
        msg.radio_switch = struct.unpack('<B', data[144: 145])[0]
        msg.radio_time = struct.unpack('<B', data[145: 146])[0]
        return msg


class MsgParam(object):
    def __init__(self):
        self.cmd_count = 0
        self.cmds = ""

    @staticmethod
    def parse_data(data):
        msg = MsgParam()
        msg.cmd_count = struct.unpack('<B', data[0: 1])[0]
        msg.cmds = data[1: -1].decode("utf-8")
        return msg
