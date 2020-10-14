'''
wayv_air_device_api.py
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

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtTest
import datetime
import copy
import os
from model.project import Project
from worker.worker_485 import Worker485
from worker.worker_wifi import WorkerWifi
from worker.msg.msg_detail import *
from worker.msg.msg_tlv import MsgTlv


MODE_485 = 0  # should get this from worker?
MODE_WIFI = 1  # should get this from worker?
ROUTER = 1
DIRECT = 2

class Wayv_Air_Radar():
    def __init__(self, ser_no):
        self.ser_no = ser_no
        self.ready = False  # this is meant to mirror QBrush(Qt.green) or QBrush(Qt.red) in vave.py
        self.targets = []
        self.targets_recvd = False  # flag that can be used to tell the app that target data has been received
        self.point_cloud = []
        self.points_recvd = False  # flag that can be used to tell the app that point cloud data has been received
        self.board_temp = 0
        self.voltage  = 0
        self.power = 0
        self.tx_temps = [0, 0, 0]
        self.pm_temp  = 0
        self.comm_config = MsgConfig()
        self.comm_config_recvd = False  # flag that can be used to tell the app that config has been received
        self.radar_config = MsgParam()
        self.radar_config_recvd = False  # flag that can be used to tell the app that config has been received
        self.progress = -1  # use negative numbers to indicate acknowledged completion
        self.fw_version = ''
        self.sbl_version = ''

class Wayv_Air_API():
    def __init__(self, t_callback, c_callback, pcl_callback, verbose, comm_mode,
                 serial_port, serial_baud, RS485_ID, ip, detail_target_enable):
        self.receiver = None
        self.clients = None
        self.project = Project()
        self.project.work_mode = comm_mode  # MODE_485=0 or MODE_WIFI=1
        self.project.serial_com = serial_port  # initialize this variable even if using WiFi
        self.project.serial_baud = serial_baud
        if detail_target_enable == 1:
            self.project.detail_target = True
        else:
            self.project.detail_target = False
        self.t_callback_fcn = t_callback
        self.c_callback_fcn = c_callback
        self.pcl_callback_fcn = pcl_callback
        self.id_485 = str(RS485_ID)
        self.ip = ip
        self.verbose = verbose
        self.radars = {}  # this is a dictionary of Wayv_Air_Radar objects

    def radar_connect(self):
        if self.receiver is None:
            if self.project.work_mode == MODE_485:
                self.project.rconfigs = self.project.rconfigs_485
                self.receiver = Worker485(self.project.serial_com, self.project.serial_baud,
                                          list(self.project.rconfigs_485.keys()),
                                          self.project.radar_timeout, self.project.comm_timeout,
                                          detail_target=self.project.detail_target,
                                          packet_size=self.project.packet_size)
                self.clients = self.receiver.device_states
            else:
                if self.ip is None:
                    return
                if self.project.work_mode == MODE_WIFI:
                    self.project.rconfigs = self.project.rconfigs_wifi
                    self.receiver = WorkerWifi(self.ip, self.project.wifi_server_port,
                                               self.project.radar_timeout, self.project.comm_timeout,
                                               detail_target=self.project.detail_target,
                                               packet_size=self.project.packet_size)
                    self.clients = self.receiver.dict_clients
            if self.receiver is None or not self.receiver.init():
                print('Error: radar not connected')
                self.receiver = None
                return
            # set up receiver thread
            self.receiver.msg_signal.connect(self.new_msg)
            # self.receiver.progress_result_signal.connect(self.print_result)
            self.receiver.progress_rate_signal.connect(self.print_progress)
            self.receiver.client_exit_signal.connect(self.dummy_radar_out)
            self.receiver.start()

            # In RS485 mode, the user has to manually add a radar to the GUI; this is analogous to that
            # TODO: accept a list of RS485 ID's
            if self.project.work_mode == MODE_485:
                if self.receiver is not None:
                    self.receiver.add_485id(self.id_485)

    def print_result(self, id, kind, result):
        if result != "":
            print(result)  # not sure what to do with this

    def print_progress(self, id, kind, rate):
        if self.verbose:
            if rate < 100:
                p_end = '\r'
            else:
                p_end = '\n'
            print(" Progress:", rate, "%", end = p_end)
        self.radars[id].progress = rate  # could be polled by the application

    def dummy_radar_out(self):
        return

    def radar_disconnect(self, id):
        if self.receiver is not None:
            self.receiver.del_485id(id)  # not sure if this is necessary
            self.receiver.end()
            self.receiver = None
        del self.radars[id]


    def query_config(self, id):
        if self.receiver is None:
            print("Error: can't retrieve config; no radar connected")
        else:
            self.progressWnd = None
            self.receiver.query(id)

    def new_msg(self, id, msg):
        # id: radar sending the message
        if isinstance(msg, MsgVersion):
            if self.project.work_mode == MODE_485 or self.project.work_mode == MODE_WIFI:
                # msg.device_id: radar device ID
                # msg: firmware version, SBL version
                print("Wayv Air", msg.device_id, "connected as ID", id)
                # print(str(msg))
                if id not in self.radars.keys():
                    self.radars[id] = Wayv_Air_Radar(msg.device_id)
                for ver in msg.versions:
                    if ver.soft_name == "Firmware":
                        self.radars[id].fw_version = "%d.%d.%d" % (ver.ver_main, ver.ver_child, ver.ver_sec)
                    elif ver.soft_name == "SBL":
                        self.radars[id].sbl_version = "%d.%d.%d" % (ver.ver_main, ver.ver_child, ver.ver_sec)
                self.radars[id].ready = True
                if self.c_callback_fcn is not "none":
                    self.c_callback_fcn(id)

        elif isinstance(msg, MsgTarget) or isinstance(msg, MsgDetailTarget):
            if id in list(self.radars.keys()):  # prevent key error after radar_disconnect
                # msg: see msg_detail.py
                self.radars[id].targets = copy.deepcopy(msg.tags[0].targets)
                self.radars[id].board_temp = msg.tags[0].temp
                self.radars[id].voltage = msg.tags[0].vol/1000
                self.radars[id].power = msg.tags[0].power
                self.radars[id].tx_temps = [msg.tags[0].tem_tx1, msg.tags[0].tem_tx2, msg.tags[0].tem_tx3]
                self.radars[id].pm_temp = msg.tags[0].tem_pm
                if msg.tags[0].target_count > 0:
                    self.radars[id].targets_recvd = True
                if self.verbose:
                    print(id)
                    print(msg.tags[0].targets)
                    print(str(msg.tags[0]))
                if self.t_callback_fcn is not "none":
                    self.t_callback_fcn(id)

        elif isinstance(msg, MsgConfig):
            # see worker/msg msg_detail.py
            self.radars[id].comm_config = copy.deepcopy(msg)
            self.radars[id].comm_config_recvd = True

        elif isinstance(msg, MsgParam):
            # see worker/msg msg_detail.py
            self.radars[id].radar_config.cmd_count = msg.cmd_count
            self.radars[id].radar_config.cmds = msg.cmds.split('\n')
            self.radars[id].radar_config_recvd = True

        elif isinstance(msg, MsgTlv):
            call_pcl_cb = False
            call_t_cb = False
            for tlv in msg.tlvs:
                if isinstance(tlv, MsgPointCloud):
                    if id in list(self.radars.keys()):
                        self.radars[id].points_recvd = True
                        self.radars[id].points = copy.deepcopy(tlv.point_clouds)
                        call_pcl_cb = True  # wait until all messages are parsed to to call callback

                elif isinstance(tlv, MsgTargetObject):
                    # Target message in point cloud mode
                    if id in list(self.radars.keys()):
                        self.radars[id].targets_recvd = True
                        self.radars[id].targets = []
                        for targ in tlv.target_objects:
                            self.radars[id].targets.append(MsgDebugTarget)
                            self.radars[id].targets[-1].tid = targ.tid
                            self.radars[id].targets[-1].x = targ.posX
                            self.radars[id].targets[-1].y = targ.posY
                            self.radars[id].targets[-1].z = targ.posZ
                            self.radars[id].targets[-1].vel_x = targ.velX
                            self.radars[id].targets[-1].vel_y = targ.velY
                            self.radars[id].targets[-1].vel_z = targ.velZ
                            call_t_cb = True  # wait until all messages are parsed to to call callback

            if self.pcl_callback_fcn is not "none" and call_pcl_cb:
                self.pcl_callback_fcn(id)

            if self.t_callback_fcn is not "none" and call_t_cb:
                self.t_callback_fcn(id)


    def send_config(self, cfg_filter, cmds):
        self.radars[cfg_filter].progress = 0
        self.radars[cfg_filter].ready = False
        print("Updating configuration for", cfg_filter)
        self.receiver.cfg_config(cmds, cfg_filter)

    def update_firmware(self, id, file):
        if self.receiver is None:
            print("Error: no radar is connected; cannot update firmware")
        else:
            if os.path.exists(file) and file.split('.')[-1] == 'bin':
                self.radars[id].progress = 0
                self.radars[id].ready = False
                print("Updating Radar Firmware")
                self.receiver.firm_update(file, id)

            else:
                print("Error: please specify a valid path to the firmware .bin file")

    def modify_comm_config(self, id, file):
        # Check to make sure that we're starting from a good config.
        # We shouldn't require that the customer send the whole config because they
        # would have to specify the device's serial number as the direct wifi netowrk.
        # The whole config must be sent, so we'll take parts not specified in the file
        # from the existing config.
        self.radars[id].comm_config_recvd = False
        self.query_config(id)
        while self.radars[id].comm_config_recvd == False:
            QtTest.QTest.qWait(100)  # wait some ms for the fresh config read
        if ((self.radars[id].comm_config.wifi_mode != ROUTER and self.radars[id].comm_config.wifi_mode != DIRECT)
            and self.radars[id].comm_config.dev_id == ''):
            print("Error: invalid comm. config read; not sending new config")
            return

        new_cfg = copy.deepcopy(self.radars[id].comm_config)

        # Open the .net file and load the modified paramters
        config = [line.rstrip('\r\n') for line in open(file)]
        for n in range(len(config)):
            if config[n].split(' ')[0] in new_cfg.__dict__.keys():
                setattr(new_cfg, config[n].split(' ')[0], config[n].split(' ')[1])
        if self.verbose:
            for item in new_cfg.__dict__.items():
                print(item)

        # format the config into a string in the correct order
        cmds = ('DevConf' + ' ' + str(new_cfg.id_485) + ' ' + str(new_cfg.dev_id) + ' ' +
                str(new_cfg.baud_485) + ' ' + new_cfg.server_ip + ' ' + str(new_cfg.server_port)
                + ' ' + str(new_cfg.dev_id) + ' 12345678' + ' ' + new_cfg.con_wifi_name
                + ' ' + new_cfg.con_wifi_pwd + ' ' + str(new_cfg.wifi_mode))

        self.send_config(id, cmds)

    def modify_param_config(self, id, file):
        # Open the .cfg file and load the modified paramters
        cmds = ''
        for line in open(file):
            cmds += line
        self.send_config(id, cmds)

    def enable_pcl(self, id):
        cmd = 'workMode 2 0'  # only allow temporary changes (0)
        self.send_config(id, cmd)
        QtTest.QTest.qWait(1500)  # wait for the config to finish before changing modes
        if self.receiver is not None:
            self.receiver.cloud_mode = True
