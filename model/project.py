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
import xml.dom.minidom
import codecs
import logging
from sys import platform
from worker.worker_base import *
from Language.Translator import global_translator


class GI(object):
    pass

    # DEBUG，INFO，WARNING，ERROR，CRITICAL
    log_level = logging.DEBUG

    log_format = u'%(asctime)s - %(msecs)d - %(name)s - %(lineno)s - %(levelname)s - %(message)s'
    log_main_module = "main"
    log_file_name = "log.txt"
    log_bak_file_name = "log.bk"
    log_date_format = '[%Y-%m_%d %H:%M:%S]'
    log_formatter = logging.Formatter(log_format, log_date_format)


logger = logging.getLogger(GI.log_main_module + '.' + __name__)
logger.setLevel(GI.log_level)


class RConfig(object):
    def __init__(self):
        # 雷达水平偏角
        self.r_h_agl = 0
        # 雷达垂直倾角
        self.r_v_agl = 0
        # 背景图片
        self.bk_pic = ""
        # 背景实际宽
        self.bk_w = 10
        # 背景实际高
        self.bk_h = 5
        # 雷达水平位置
        self.r_x_offset = 5
        # 雷达垂直位置
        self.r_y_offset = 4.8
        # 注释
        self.remarks = ""


class SceneConfig(object):
    def __init__(self):
        # 名称
        self.name = ""
        # 背景图片
        self.pic_path = ""
        # 背景实际宽
        self.width = 10
        # 背景实际高
        self.height = 5
        #
        self.radars = {}


class SceneRadarConfig(object):
    def __init__(self):
        #
        self.desc = ""
        # 雷达水平位置
        self.x_pos = 5
        # 雷达垂直位置
        self.y_pos = 4.8
        # 雷达水平偏角
        self.h_agl = 0
        # 雷达垂直倾角
        self.v_agl = 0
        # 备注
        self.remarks = ""


class TestConfig(object):
    def __init__(self):
        #
        self.ver_sbl = "2.0.4"
        self.ver_firm = "2.0.12"
        # 生产数据库
        self.db_host = "localhost"
        self.db_port = 3306
        self.db_user = ""
        self.db_pwd = ""
        self.db_name = ""
        # 供电
        self.vol_l_1 = 11.9
        self.vol_u_1 = 12.1
        self.cur_l_1 = 0.1
        self.cur_u_1 = 0.3
        self.vol_l_2 = 11.9
        self.vol_u_2 = 12.1
        self.cur_l_2 = 0.1
        self.cur_u_2 = 0.3
        # 数据
        self.power_l = [0] * 12
        self.power_u = [0] * 12
        self.dis_l = [0] * 12
        self.dis_u = [0] * 12
        self.doppler_l = [0] * 12
        self.doppler_u = [0] * 12
        self.noise1_l = [0] * 12
        self.noise1_u = [0] * 12
        self.noise2_l = [0] * 12
        self.noise2_u = [0] * 12
        self.noise3_l = [0] * 12
        self.noise3_u = [0] * 12
        self.sub_l = [0] * 12
        self.sub_u = [0] * 12
        #
        self.radar_com = ""
        self.power_com = ""
        self.turntable_com = ""


SOFTWARE_VERSION = "1.200.1.11"


class Project(object):
    def __init__(self):
        self.project_version = 3
        self.soft_version = SOFTWARE_VERSION
        # 雷达配置列表 key为唯一描述符 value为rconfig对象
        self.rconfigs_485 = {}
        self.rconfigs_wifi = {}
        self.rconfigs_jzq = {}
        self.rconfigs = None
        # 情景模式配置列表
        self.sconfigs = {}
        # 工作模式
        self.work_mode = MODE_485
        # 485id自动检测最大id
        self.autodetect_maxid = 10
        # jzq模式线路id列表
        self.jzq_lines = [1, 2, 3, 4]
        # 串口信息
        if 'linux' in platform:
            self.serial_com = "/dev/ttyUSB0"
        else:
            self.serial_com = "COM5"
        self.serial_baud = 115200
        # wifi server信息
        self.wifi_server_port = 8877
        # 集中器 server信息
        self.jzq_server_port = 8087
        #
        self.his_max = 10
        # 身份确认超时时间
        self.radar_timeout = 1
        # 通讯超时时间
        self.comm_timeout = 0.6
        # 升级包大小
        self.packet_size = 128
        # 测试配置
        self.tconfig = TestConfig()
        # 数据库
        self.use_db = False
        self.db_host = ""
        self.db_port = 3306
        self.db_user = ""
        self.db_pwd = ""
        self.db_name = ""
        #
        self.debug_target = False
        self.detail_target = False

    def save(self, path):
        try:
            dom = xml.dom.minidom.Document()
            root_node = dom.createElement('project')
            dom.appendChild(root_node)

            common_node = dom.createElement('common')
            root_node.appendChild(common_node)
            common_node.setAttribute('version', str(self.project_version))
            common_node.setAttribute('work_mode', str(self.work_mode))
            common_node.setAttribute('serial_com', self.serial_com)
            common_node.setAttribute('serial_baud', str(self.serial_baud))
            common_node.setAttribute('wifi_server_port', str(self.wifi_server_port))
            common_node.setAttribute('jzq_server_port', str(self.jzq_server_port))
            common_node.setAttribute("his_max", str(self.his_max))
            common_node.setAttribute("radar_timeout", str(self.radar_timeout))
            common_node.setAttribute("comm_timeout", str(self.comm_timeout))
            common_node.setAttribute("use_db", "True" if self.use_db else "False")
            common_node.setAttribute("db_host", self.db_host)
            common_node.setAttribute("db_port", "%d" % self.db_port)
            common_node.setAttribute("db_user", self.db_user)
            common_node.setAttribute("db_pwd", Project.my_encode(self.db_pwd))
            common_node.setAttribute("db_name", self.db_name)
            common_node.setAttribute("debug_target", "1" if self.debug_target else "0")
            common_node.setAttribute("packet_size", str(self.packet_size))

            rconfigs_node = dom.createElement('rconfigs_485')
            root_node.appendChild(rconfigs_node)
            for desc, rconfig in self.rconfigs_485.items():
                rconfig_node = dom.createElement('rconfig')
                rconfigs_node.appendChild(rconfig_node)
                rconfig_node.setAttribute("desc", desc)
                rconfig_node.setAttribute("r_h_agl", "%.2f" % rconfig.r_h_agl)
                rconfig_node.setAttribute("r_v_agl", "%.2f" % rconfig.r_v_agl)
                rconfig_node.setAttribute("remarks", rconfig.remarks)
                rconfig_node.setAttribute("bk_w", "%.2f" % rconfig.bk_w)
                rconfig_node.setAttribute("bk_h", "%.2f" % rconfig.bk_h)
                rconfig_node.setAttribute("bk_pic", rconfig.bk_pic)
                rconfig_node.setAttribute("r_x_offset", "%.2f" % rconfig.r_x_offset)
                rconfig_node.setAttribute("r_y_offset", "%.2f" % rconfig.r_y_offset)

            rconfigs_node = dom.createElement('rconfigs_wifi')
            root_node.appendChild(rconfigs_node)
            for desc, rconfig in self.rconfigs_wifi.items():
                rconfig_node = dom.createElement('rconfig')
                rconfigs_node.appendChild(rconfig_node)
                rconfig_node.setAttribute("desc", desc)
                rconfig_node.setAttribute("r_h_agl", "%.2f" % rconfig.r_h_agl)
                rconfig_node.setAttribute("r_v_agl", "%.2f" % rconfig.r_v_agl)
                rconfig_node.setAttribute("remarks", rconfig.remarks)
                rconfig_node.setAttribute("bk_w", "%.2f" % rconfig.bk_w)
                rconfig_node.setAttribute("bk_h", "%.2f" % rconfig.bk_h)
                rconfig_node.setAttribute("bk_pic", rconfig.bk_pic)
                rconfig_node.setAttribute("r_x_offset", "%.2f" % rconfig.r_x_offset)
                rconfig_node.setAttribute("r_y_offset", "%.2f" % rconfig.r_y_offset)

            rconfigs_node = dom.createElement('rconfigs_jzq')
            root_node.appendChild(rconfigs_node)
            for desc, rconfig in self.rconfigs_jzq.items():
                rconfig_node = dom.createElement('rconfig')
                rconfigs_node.appendChild(rconfig_node)
                rconfig_node.setAttribute("desc", desc)
                rconfig_node.setAttribute("r_h_agl", "%.2f" % rconfig.r_h_agl)
                rconfig_node.setAttribute("r_v_agl", "%.2f" % rconfig.r_v_agl)
                rconfig_node.setAttribute("remarks", rconfig.remarks)
                rconfig_node.setAttribute("bk_w", "%.2f" % rconfig.bk_w)
                rconfig_node.setAttribute("bk_h", "%.2f" % rconfig.bk_h)
                rconfig_node.setAttribute("bk_pic", rconfig.bk_pic)
                rconfig_node.setAttribute("r_x_offset", "%.2f" % rconfig.r_x_offset)
                rconfig_node.setAttribute("r_y_offset", "%.2f" % rconfig.r_y_offset)

            sconfigs_node = dom.createElement('sconfigs')
            root_node.appendChild(sconfigs_node)
            for name, sconfig in self.sconfigs.items():
                sconfig_node = dom.createElement('sconfig')
                sconfigs_node.appendChild(sconfig_node)
                sconfig_node.setAttribute("name", name)
                sconfig_node.setAttribute("pic_path", sconfig.pic_path)
                sconfig_node.setAttribute("width", "%.2f" % sconfig.width)
                sconfig_node.setAttribute("height", "%.2f" % sconfig.height)
                for desc, srconfig in sconfig.radars.items():
                    srconfig_node = dom.createElement("srconfig")
                    sconfig_node.appendChild(srconfig_node)
                    srconfig_node.setAttribute("desc", desc)
                    srconfig_node.setAttribute("x_pos", "%.2f" % srconfig.x_pos)
                    srconfig_node.setAttribute("y_pos", "%.2f" % srconfig.y_pos)
                    srconfig_node.setAttribute("remarks", srconfig.remarks)
                    srconfig_node.setAttribute("h_agl", "%.2f" % srconfig.h_agl)
                    srconfig_node.setAttribute("v_agl", "%.2f" % srconfig.v_agl)

            tconfigs_node = dom.createElement('tconfig')
            root_node.appendChild(tconfigs_node)
            tconfigs_node.setAttribute("ver_sbl", self.tconfig.ver_sbl)
            tconfigs_node.setAttribute("ver_firm", self.tconfig.ver_firm)
            tconfigs_node.setAttribute("db_host", self.tconfig.db_host)
            tconfigs_node.setAttribute("db_port", "%d" % self.tconfig.db_port)
            tconfigs_node.setAttribute("db_user", self.tconfig.db_user)
            tconfigs_node.setAttribute("db_pwd", Project.my_encode(self.tconfig.db_pwd))
            tconfigs_node.setAttribute("db_name", self.tconfig.db_name)
            tconfigs_node.setAttribute("vol_l_1", "%.3f" % self.tconfig.vol_l_1)
            tconfigs_node.setAttribute("vol_u_1", "%.3f" % self.tconfig.vol_u_1)
            tconfigs_node.setAttribute("cur_l_1", "%.3f" % self.tconfig.cur_l_1)
            tconfigs_node.setAttribute("cur_u_1", "%.3f" % self.tconfig.cur_u_1)
            tconfigs_node.setAttribute("vol_l_2", "%.3f" % self.tconfig.vol_l_2)
            tconfigs_node.setAttribute("vol_u_2", "%.3f" % self.tconfig.vol_u_2)
            tconfigs_node.setAttribute("cur_l_2", "%.3f" % self.tconfig.cur_l_2)
            tconfigs_node.setAttribute("cur_u_2", "%.3f" % self.tconfig.cur_u_2)
            tconfigs_node.setAttribute("power_l", ";".join([str(x) for x in self.tconfig.power_l]))
            tconfigs_node.setAttribute("power_u", ";".join([str(x) for x in self.tconfig.power_u]))
            tconfigs_node.setAttribute("dis_l", ";".join([str(x) for x in self.tconfig.dis_l]))
            tconfigs_node.setAttribute("dis_u", ";".join([str(x) for x in self.tconfig.dis_u]))
            tconfigs_node.setAttribute("doppler_l", ";".join([str(x) for x in self.tconfig.doppler_l]))
            tconfigs_node.setAttribute("doppler_u", ";".join([str(x) for x in self.tconfig.doppler_u]))
            tconfigs_node.setAttribute("noise1_l", ";".join([str(x) for x in self.tconfig.noise1_l]))
            tconfigs_node.setAttribute("noise1_u", ";".join([str(x) for x in self.tconfig.noise1_u]))
            tconfigs_node.setAttribute("noise2_l", ";".join([str(x) for x in self.tconfig.noise2_l]))
            tconfigs_node.setAttribute("noise2_u", ";".join([str(x) for x in self.tconfig.noise2_u]))
            tconfigs_node.setAttribute("noise3_l", ";".join([str(x) for x in self.tconfig.noise3_l]))
            tconfigs_node.setAttribute("noise3_u", ";".join([str(x) for x in self.tconfig.noise3_u]))
            tconfigs_node.setAttribute("sub_l", ";".join([str(x) for x in self.tconfig.sub_l]))
            tconfigs_node.setAttribute("sub_u", ";".join([str(x) for x in self.tconfig.sub_u]))
            tconfigs_node.setAttribute("radar_com", self.tconfig.radar_com)
            tconfigs_node.setAttribute("power_com", self.tconfig.power_com)
            tconfigs_node.setAttribute("turntable_com", self.tconfig.turntable_com)
            f = codecs.open(path, 'w', 'utf-8')
            dom.writexml(f, indent='', addindent='\t', newl='\n', encoding='utf-8')
            f.close()
        except Exception as e:
            logger.error(e)
            return None

    def load(self, path):
        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
                dom = xml.dom.minidom.parseString(content)
                root = dom.documentElement
                for node in root.childNodes:
                    if node.nodeName == 'common':
                        attrs = node.attributes.keys()
                        self.project_version = int(node.getAttribute("version"))
                        if "work_mode" in attrs:
                            self.work_mode = int(node.getAttribute("work_mode"))
                        else:
                            self.work_mode = MODE_485
                        self.serial_com = node.getAttribute("serial_com")
                        self.serial_baud = int(node.getAttribute("serial_baud"))
                        self.wifi_server_port = int(node.getAttribute("wifi_server_port"))
                        self.jzq_server_port = int(node.getAttribute("jzq_server_port"))
                        use_db = node.getAttribute("use_db")
                        self.use_db = True if use_db.lower() == "true" else False
                        try:
                            self.his_max = int(node.getAttribute("his_max"))
                        except Exception:
                            self.his_max = 3306
                        try:
                            self.radar_timeout = float(node.getAttribute("radar_timeout"))
                        except Exception:
                            self.radar_timeout = 1
                        try:
                            self.comm_timeout = float(node.getAttribute("comm_timeout"))
                        except Exception:
                            self.comm_timeout = 0.2
                        try:
                            self.debug_target = True if node.getAttribute("debug_target") == "1" else False
                        except Exception:
                            self.debug_target = False
                        try:
                            self.packet_size = int(node.getAttribute("packet_size"))
                        except Exception:
                            self.packet_size = 128
                        #
                        self.db_host = node.getAttribute("db_host")
                        try:
                            self.db_port = int(node.getAttribute("db_port"))
                        except Exception:
                            self.db_port = 3306
                        self.db_user = node.getAttribute("db_user")
                        self.db_pwd = Project.my_decode(node.getAttribute("db_pwd"))
                        self.db_name = node.getAttribute("db_name")
                    elif node.nodeName == "sconfigs":
                        for subnode in node.childNodes:
                            if subnode.nodeName == 'sconfig':
                                sconfig = SceneConfig()
                                sconfig.name = subnode.getAttribute("name")
                                sconfig.pic_path = subnode.getAttribute("pic_path")
                                sconfig.width = float(subnode.getAttribute("width"))
                                sconfig.height = float(subnode.getAttribute("height"))
                                self.sconfigs[sconfig.name] = sconfig
                                for ssubnode in subnode.childNodes:
                                    if ssubnode.nodeName == "srconfig":
                                        srconfig = SceneRadarConfig()
                                        srconfig.desc = ssubnode.getAttribute("desc")
                                        srconfig.remarks = ssubnode.getAttribute("remarks")
                                        srconfig.x_pos = float(ssubnode.getAttribute("x_pos"))
                                        srconfig.y_pos = float(ssubnode.getAttribute("y_pos"))
                                        srconfig.h_agl = float(ssubnode.getAttribute("h_agl"))
                                        srconfig.v_agl = float(ssubnode.getAttribute("v_agl"))
                                        sconfig.radars[srconfig.desc] = srconfig
                    elif node.nodeName == 'rconfigs_485':
                        for subnode in node.childNodes:
                            if subnode.nodeName == 'rconfig':
                                rconfig = RConfig()
                                self.rconfigs_485[subnode.getAttribute("desc")] = rconfig
                                rconfig.r_h_agl = float(subnode.getAttribute("r_h_agl"))
                                rconfig.r_v_agl = float(subnode.getAttribute("r_v_agl"))
                                rconfig.remarks = subnode.getAttribute("remarks")
                                rconfig.bk_w = float(subnode.getAttribute("bk_w"))
                                rconfig.bk_h = float(subnode.getAttribute("bk_h"))
                                rconfig.bk_pic = subnode.getAttribute("bk_pic")
                                rconfig.r_x_offset = float(subnode.getAttribute("r_x_offset"))
                                rconfig.r_y_offset = float(subnode.getAttribute("r_y_offset"))
                    elif node.nodeName == 'rconfigs_wifi':
                        for subnode in node.childNodes:
                            if subnode.nodeName == 'rconfig':
                                rconfig = RConfig()
                                self.rconfigs_wifi[subnode.getAttribute("desc")] = rconfig
                                rconfig.r_h_agl = float(subnode.getAttribute("r_h_agl"))
                                rconfig.r_v_agl = float(subnode.getAttribute("r_v_agl"))
                                rconfig.remarks = subnode.getAttribute("remarks")
                                rconfig.bk_w = float(subnode.getAttribute("bk_w"))
                                rconfig.bk_h = float(subnode.getAttribute("bk_h"))
                                rconfig.bk_pic = subnode.getAttribute("bk_pic")
                                rconfig.r_x_offset = float(subnode.getAttribute("r_x_offset"))
                                rconfig.r_y_offset = float(subnode.getAttribute("r_y_offset"))
                    elif node.nodeName == 'rconfigs_jzq':
                        for subnode in node.childNodes:
                            if subnode.nodeName == 'rconfig':
                                rconfig = RConfig()
                                self.rconfigs_jzq[subnode.getAttribute("desc")] = rconfig
                                rconfig.r_h_agl = float(subnode.getAttribute("r_h_agl"))
                                rconfig.r_v_agl = float(subnode.getAttribute("r_v_agl"))
                                rconfig.remarks = subnode.getAttribute("remarks")
                                rconfig.bk_w = float(subnode.getAttribute("bk_w"))
                                rconfig.bk_h = float(subnode.getAttribute("bk_h"))
                                rconfig.bk_pic = subnode.getAttribute("bk_pic")
                                rconfig.r_x_offset = float(subnode.getAttribute("r_x_offset"))
                                rconfig.r_y_offset = float(subnode.getAttribute("r_y_offset"))
                    elif node.nodeName == "tconfig":
                        tconfig = TestConfig()
                        tconfig.ver_sbl = node.getAttribute("ver_sbl")
                        if tconfig.ver_sbl == "":
                            tconfig.ver_sbl = "2.0.4"
                        tconfig.ver_firm = node.getAttribute("ver_firm")
                        if tconfig.ver_firm == "":
                            tconfig.ver_firm = "2.0.12"
                        tconfig.db_host = node.getAttribute("db_host")
                        tconfig.db_port = int(node.getAttribute("db_port"))
                        tconfig.db_user = node.getAttribute("db_user")
                        tconfig.db_pwd = Project.my_decode(node.getAttribute("db_pwd"))
                        tconfig.db_name = node.getAttribute("db_name")
                        tconfig.vol_l_1 = float(node.getAttribute("vol_l_1"))
                        tconfig.vol_u_1 = float(node.getAttribute("vol_u_1"))
                        tconfig.cur_l_1 = float(node.getAttribute("cur_l_1"))
                        tconfig.cur_u_1 = float(node.getAttribute("cur_u_1"))
                        tconfig.vol_l_2 = float(node.getAttribute("vol_l_2"))
                        tconfig.vol_u_2 = float(node.getAttribute("vol_u_2"))
                        tconfig.cur_l_2 = float(node.getAttribute("cur_l_2"))
                        tconfig.cur_u_2 = float(node.getAttribute("cur_u_2"))
                        tconfig.dis_l = [int(x) for x in node.getAttribute("dis_l").split(";")]
                        tconfig.dis_u = [int(x) for x in node.getAttribute("dis_u").split(";")]
                        tconfig.power_l = [int(x) for x in node.getAttribute("power_l").split(";")]
                        tconfig.power_u = [int(x) for x in node.getAttribute("power_u").split(";")]
                        tconfig.doppler_l = [int(x) for x in node.getAttribute("doppler_l").split(";")]
                        tconfig.doppler_u = [int(x) for x in node.getAttribute("doppler_u").split(";")]
                        tconfig.noise1_l = [int(x) for x in node.getAttribute("noise1_l").split(";")]
                        tconfig.noise1_u = [int(x) for x in node.getAttribute("noise1_u").split(";")]
                        tconfig.noise2_l = [int(x) for x in node.getAttribute("noise2_l").split(";")]
                        tconfig.noise2_u = [int(x) for x in node.getAttribute("noise2_u").split(";")]
                        tconfig.noise3_l = [int(x) for x in node.getAttribute("noise3_l").split(";")]
                        tconfig.noise3_u = [int(x) for x in node.getAttribute("noise3_u").split(";")]
                        tconfig.sub_l = [int(x) for x in node.getAttribute("sub_l").split(";")]
                        tconfig.sub_u = [int(x) for x in node.getAttribute("sub_u").split(";")]
                        tconfig.radar_com = node.getAttribute("radar_com")
                        tconfig.power_com = node.getAttribute("power_com")
                        tconfig.turntable_com = node.getAttribute("turntable_com")
                        self.tconfig = tconfig
        except Exception as e:
            logger.error(e)
            return False
        else:
            return True

    @staticmethod
    def my_decode(_text):
        if len(_text) > 1:
            segs = _text[0: -1].split(";")
            bs = bytearray(len(segs))
            for i in range(len(segs)):
                bs[i] = int(segs[i]) - i * i - 1
            return bytes(bs).decode(encoding="utf-8")
        else:
            return ""

    @staticmethod
    def my_encode(_text):
        res = ""
        bs = _text.encode(encoding="utf-8")
        for i in range(len(bs)):
            res += "%d;" % (bs[i] + i * i + 1)
        return res


if __name__ == "__main__":
    str_encode = Project.my_encode("root")
    print(str_encode)
