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
from PyQt5.QtCore import *
import time


MODE_485 = 0
MODE_WIFI = 1
MODE_JZQ = 2

PROGRESS_TYPE_CFG = 1
PROGRESS_TYPE_FIRM = 2
PROGRESS_TYPE_SBL = 3

ID_RESET = 0
ID_ADD = 1
ID_DEL = 2


# 通讯基类
class WorkerBase(QThread):

    # 客户端退出信号 参数：唯一描述
    client_exit_signal = pyqtSignal(str)
    # 参数：唯一描述(ip+id_line+id_485)，消息对象
    msg_signal = pyqtSignal(str, object)
    # 结果信号 参数：唯一描述，类型（1 cfg 2 固件），结果（成功为空，失败为描述）
    progress_result_signal = pyqtSignal(str, int, str)
    # 进度信号 参数：唯一描述，类型（1 cfg 2 固件），百分比（0-100）
    progress_rate_signal = pyqtSignal(str, int, int)

    def __init__(self):
        super(WorkerBase, self).__init__()
        #
        self.is_run = True
        # cfg命令列表 过滤器
        self.cfg_cmds = None
        self.cfg_filter = None
        # 固件路径 过滤器
        self.firm_path = None
        self.firm_filter = None
        # SBL路径 过滤器
        self.sbl_path = None
        self.sbl_filter = None
        # 杂波滤除 clutter filter
        self.filter_region = None
        self.filter_filter = None
        # 查询 id
        self.query_desc = None

    def end(self):
        self.is_run = False
        self.wait(msecs=10000)
        return True

    def run(self):
        pass


# 设备状态 通过获取版本号来判断是否为雷达
class DeviceState(object):
    def __init__(self):
        # 是否需要获取版本号
        self.__need_get_version = True
        # 是否雷达设备
        self.__is_radar = False
        #
        self.__reset_time = 0
        #
        self.__get_version_times = 0
        #
        self.__get_target_time = 0
        # 获取目标错误次数
        self.error_count = 0

    def reset(self):
        """
        重置设备，需要重新要版本号以确定设备是否为雷达
        :return:
        """
        self.__need_get_version = True
        self.__is_radar = False
        self.__reset_time = 0
        self.__get_version_times = 0

    def need_get_version(self):
        """
        是否需要索要版本号
        :return:
        """
        # 从重置开始尝试6次，每次间隔时间不小于5秒
        if not self.__need_get_version:
            # 每隔5分钟，重新探测一次
            if time.time() - self.__reset_time >= 60 * 5:
                self.reset()
            return False
        else:
            if time.time() - self.__reset_time >= 5:
                self.__get_version_times += 1
                self.__reset_time = time.time()
                if self.__get_version_times >= 6:
                    self.__need_get_version = False
                return True
            else:
                return False

    def need_get_target(self):
        if time.time() - self.__get_target_time >= 0.05:
            self.__get_target_time = time.time()
            return True
        else:
            return False

    def is_radar(self):
        """
        设备是否为雷达
        :return:
        """
        return self.__is_radar

    def set_radar(self):
        """
        判定设备为雷达，无需再去索要版本号
        :return:
        """
        self.__is_radar = True
        self.__need_get_version = False
