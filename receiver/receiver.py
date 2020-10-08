# -*- coding: utf-8 -*-
from PyQt5 import QtCore
import logging
from model.project import GI

logger = logging.getLogger(GI.log_main_module + '.' + __name__)
logger.setLevel(GI.log_level)

class Receiver(QtCore.QThread):
    """
    数据接收器，基类，子类需要重写各函数（prepare，destroy，recv_data）
    """

    # 数据信号
    data_signal = QtCore.pyqtSignal(str, object)
    # cfg下发状态信号
    cfg_result_signal = QtCore.pyqtSignal(str, str)
    cfg_progress_signal = QtCore.pyqtSignal(str, int)
    # 固件更新状态信号
    firm_result_signal = QtCore.pyqtSignal(str, str)
    firm_progress_signal = QtCore.pyqtSignal(str, int)
    # 客户端退出信号
    client_exit_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        """
        构造函数
        """
        super(Receiver, self).__init__()
        self.is_run = True
        self.is_pause = False
        self.cfg_cmds = None
        self.cfg_filter = None
        self.firmware_path = None
        self.firmware_filter = None

    def rcv_version(self, desc, device_id, version):
        pass

    def prepare(self):
        """
        初始化
        :return:
        """
        return True

    def destroy(self):
        """
        销毁
        :return:
        """
        return True

    def recv_data(self):
        """
        接收数据
        :return:
        """
        return None

    def send_data(self, data):
        """
        发送数据
        """
        return True

    def begin(self):
        """
        开始接收数据
        """
        self.start()
        return True

    def end(self):
        """
        停止接收数据
        """
        self.is_run = False
        self.wait()
        self.destroy()
        return True

    def pause(self):
        """
        暂停接收数据
        """
        self.is_pause = True
        return True

    def resume(self):
        """
        继续接收数据
        """
        self.is_pause = False
        return True

    def kick_client(self, desc):
        pass

    def send_cfg(self):
        if self.cfg_cmds is not None:
            str_cmds = self.cfg_cmds
            self.cfg_cmds = None
            ret_desc = ""
            cmds = str_cmds.split("\n")
            for cmd in cmds:
                ret = -1
                self.send_data(cmd + "\n")
                for i in range(0, 10):
                    data = self.recv_data()
                    if data is not None:
                        for j in range(0, len(data) - 3):
                            if data[j] == 0xAA and data[j + 3] == 0x55:
                                ret = data[j + 1]
                                break
                    if ret != -1:
                        break
                    self.msleep(10)
                if ret == -1:
                    ret_desc += cmd + " : no data received\r\n"
                elif ret != 0x01:
                    ret_desc += cmd + " : " + str(ret) + "\r\n"
            self.cfg_result_signal.emit(ret_desc)

    def update_firmware(self, file_path):
        pass

    def run(self):
        while self.is_run:
            if not self.is_pause:
                try:
                    # 发送cfg配置
                    self.send_cfg()
                    # 接收数据
                    raw = self.recv_data()
                    if raw is not None and len(raw) > 0:
                        self.notice(raw)
                except Exception as e:
                    logger.error(e)
            self.msleep(10)


