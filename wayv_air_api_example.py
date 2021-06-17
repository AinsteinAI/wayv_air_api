'''
wayv_air_air_example.py
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

import sys
import signal
import threading
import smokesignal
import time
import copy
import os
from worker.msg.test_msg import TestMsgFunc
from worker.msg.msg_tlv import MsgTlv
from worker.msg.msg_detail import MsgConfig, MsgDetail, MsgParam, MsgTarget, MsgTargetObject, MsgVersion
from wayv_air_device_api import Wayv_Air_API
def radar_con_callback(id):
    global new_firmware, query_config, comm_config, param_config, firmware_up, enbl_pcl, new_sbl, sbl_up
    if id not in radars_seen:
        radars_seen.append(id)
        if new_comm_config:
            comm_config.append(id)  # tell the supervisor to update this radar's comm. config
        if new_param_config:
            param_config.append(id)  # tell the supervisor to update this radar's radar parameters
        if new_firmware:
            firmware_up.append(id)  # tell the supervisor to update this radar's firmware
        if new_sbl:
            sbl_up.append(id) #tell supervisor to update SBL
        if enbl_pcl:
            wayv_air.enable_pcl(id)
    query_config.append(id)  # tell the supervisor to query the config for this radar

'''
Start user-defined code block.
User must define a callback function that will be called
when the radar receives target data.
'''
def my_target_callback(id):
    # This is called by the Wayv_Air_API class when it gets data from the radar.
    # Data processing, logging, etc. can go here

    if v_level >= 1:
        for v in wayv_air.radars.values():
            if v.targets_recvd:  # Only print targets from devices that have new targets; could also tell this from id passed to the callback
                v.targets_recvd = False
                print("New target data from", v.ser_no)

                if target_detail == 1:            ## call debug mode format for Wayv Air
                    if velocity_enable == 1:
                        if point_num_enable == 1:
                            for tar in v.targets:
                                print("target ID: %d, x: %0.2f, y: %0.2f, z: %0.2f, vx: %0.2f, vy: %0.2f, vz: %0.2f, point_num: %d"
                                       % (tar.tid, tar.x, tar.y, tar.z, tar.vel_x, tar.vel_y, tar.vel_z, tar.cp_count))
                        else:  # velocity only, not point number
                            for tar in v.targets:
                                print("target ID: %d, x: %0.2f, y: %0.2f, z: %0.2f, vx: %0.2f, vy: %0.2f, vz: %0.2f"
                                       % (tar.tid, tar.x, tar.y, tar.z, tar.vel_x, tar.vel_y, tar.vel_z))
                    elif point_num_enable == 1:  # point number, not velocity
                        for tar in v.targets:
                            print("target ID: %d, x: %0.2f, y: %0.2f, z: %0.2f, point_num: %d"
                                   % (tar.tid, tar.x, tar.y, tar.z, tar.cp_count))
                elif target_detail == 0:          ## call normal mode format for Wayv Air
                    for tar in v.targets:
                        print("target ID: %d, x: %0.2f, y: %0.2f, z: %0.2f" % (tar.tid, tar.x, tar.y, tar.z))
                else:                               ## default in  debug mode format for Wayv Air
                    for tar in v.targets:
                        print("target ID: %d, x: %0.2f, y: %0.2f, z: %0.2f, vx: %0.2f, vy: %0.2f, vz: %0.2f"
                               % (tar.tid, tar.x, tar.y, tar.z, tar.vel_x, tar.vel_y, tar.vel_z))

            if v_level >= 2:
                print("Board temperature:", v.board_temp, "℃")
                print("Tx temperatures:", v.tx_temps, "℃")
                print("PM temperature:", v.pm_temp, "℃")
                print("Voltage", v.voltage, "V")
                print("Power", v.power, "W")


def my_pcl_callback(id):
    # Data processing for the point cloud can go here.
    # Ignore this section if your Wayv Air device is not equipped with the high-speed RS-485 option
    if v_level >= 1:
        for p in wayv_air.radars[id].points:
            print("range: %0.2f, azimuth: %0.2f, elevation: %0.2f, doppler: %0.2f, snr: %d"
                   % (p.range, p.azimuth, p.elevation, p.doppler, p.snr))

def supervisor():
    # This function handles less time-sensitive operations like updating configurations
    # and firmware. It also provides a mechanism for the Python interpreter to run so the
    # signint handler can exit the program properly
    global query_config, comm_config, param_config, new_firmware, new_sbl

    for v in wayv_air.radars.values():
    # print progress updates
        if v.progress > 0:
            print(v.ser_no, "update progress:", v.progress, "%")
        if v.progress >= 100:
            v.progress = -1  # use negative numbers to indicate acknowledged completion
    # check for new config messages and acknowledge them
        if v.comm_config_recvd:
            v.comm_config_recvd = False
            # print firmware version
            if v_level >= 1:
                print("Device: ", v.ser_no, "Firmware Version:", v.fw_version)
                print("Present Comm. Config:")
                for item in v.comm_config.__dict__.items():
                    print(item)
                print("")
            if v_level >= 1:
                print("Device: ", v.ser_no, "SBL Version: ", v.sbl_version)
        if v.radar_config_recvd:
            v.radar_config_recvd = False
            if v_level >= 1:
                print("Device: ", v.ser_no, "Firmware Version:", v.fw_version)
                print("Present Radar Config: (",v.radar_config.cmd_count,"lines )")
                for item in v.radar_config.cmds:
                    print(item)
                print("")

    if len(query_config) > 0:
        id = query_config.pop(0)
        wayv_air.query_config(id)  # the API only support querying one radar at a time
    if len(comm_config) > 0:
        id = comm_config.pop(0)
        wayv_air.modify_comm_config(id, comm_file)  # only the first radar in this example
        if id not in query_config:
            query_config.append(id)
    if len(param_config) > 0:
        id = param_config.pop(0)
        wayv_air.modify_param_config(id, param_file)  # only the first radar in this example
        if id not in query_config:
            query_config.append(id)
    if len(firmware_up) > 0:
        id = firmware_up.pop(0)
        if id not in query_config:
            query_config.append(id)
        wayv_air.update_firmware(id, fw_path)
    if len(sbl_up) > 0:
        id = sbl_up.pop(0)
        if id not in query_config:
            query_config.append(id)
        wayv_air.update_sbl(id, sbl_path)

'''
End user-defined code block
'''

def sigint_handler(*args):
    sys.stderr.write('/r')
    # make a list of the radars because the dictionary will change when disconnecting radars
    radar_list = []
    for r in list(wayv_air.radars.keys()):
        radar_list.append(r)
    for r in radar_list:
        wayv_air.radar_disconnect(r) # disconnect the radar before quitting
    sys.exit()

if __name__ == "__main__":
    MODE_485 = 0
    MODE_WIFI = 1
    delay_init = 50 # number of target callbacks to pass before sending or reading configurations
    delay = delay_init
    v_level = 0
    if 'linux' in sys.platform:
        serial_port = "/dev/ttyUSB0"
    else:
        serial_port = "COM5"
    serial_baud = 115200
    comm_mode = MODE_485
    wifi_ip = '192.168.4.65'
    wifi_port = 8877
    target_detail = 0
    velocity_enable = 0
    point_num_enable = 0
    rs485_id = 1
    new_comm_config = False
    new_param_config = False
    new_firmware = False
    new_sbl = False
    enbl_pcl = False
    query_config = []
    comm_config = []
    param_config = []
    firmware_up = []
    sbl_up = []
    radars_seen = []

    help_str = (" -ip: Host WiFi IP address. Defaults to serial communication if this option is not supplied\n"
                " -wifi_port: WiFi server (host) port; must match the device's config\n"
                " -vel: Optional argument, provide this argument to read targets' velocities. Not supported in all modes \n"
                " -v, -vv, or -vvv: verbosity\n"
                " -p: serial port (ignored if -ip is used)\n"
                " -vel: read target velocit\n"
                " -point_num: read the number of points per target\n"
                " -rid: RS485 ID of the radar to connect to\n"
                " -net: path to network communication config file (.net) to be loaded\n"
                " -cfg: path to radar parameter config file (.cfg) to be loaded\n"
                " -fw: path to firmware .bin file to be loaded\n"
                " -sbl: path to the bootloader .bin file to be loaded\n"
                " -pcl: enable point cloud output from the Wayv Air\n"
                " -baud: serial baud rate; must match what the Wayv Air is already set to")

    if len(sys.argv) > 1:
        for i in range(1,len(sys.argv)):
            if sys.argv[i] == "-v":
                v_level = 1
            elif sys.argv[i] == "-vv":
                v_level = 2
            elif sys.argv[i] == "-vvv":
                v_level = 3
            elif sys.argv[i] == "-ip":
                wifi_ip = sys.argv[i+1]
                comm_mode = MODE_WIFI
            elif sys.argv[i] == "-wifi_port":
                wifi_port = int(sys.argv[i+1])
            elif sys.argv[i] == "-vel":
                velocity_enable = 1
                target_detail = 1
            elif sys.argv[i] == "-point_num":
                point_num_enable = 1
                target_detail = 1
            elif sys.argv[i] == "-p":
                serial_port = sys.argv[i+1]
            elif sys.argv[i] == "-rid":
                rs485_id = sys.argv[i+1]
            elif sys.argv[i] == "-net":
                new_comm_config = True
                comm_file = sys.argv[i+1]
                #Remove any potential whitespace that would cause os.path.exists to be false
                comm_file = comm_file.strip()
                if not os.path.exists(comm_file) or comm_file.split('.')[-1] != 'net':
                    print("Error: please specify a path to a .net file")
                    sys.exit(1)
            elif sys.argv[i] == "-cfg":
                new_param_config = True
                param_file = sys.argv[i+1]
                param_file = param_file.strip()
                if not os.path.exists(param_file) or param_file.split('.')[-1] != 'cfg':
                    print("Error: please specify a path to a .cfg file")
                    sys.exit(1)
            elif sys.argv[i] == "-fw":
                new_firmware = True
                fw_path = sys.argv[i+1]
                fw_path = fw_path.strip()
                if not os.path.exists(fw_path) or fw_path.split('.')[-1] != 'bin':
                    print("Error: please specify a path to a .bin file")
                    sys.exit(1)
            elif sys.argv[i] == "-sbl":
                new_sbl = True
                sbl_path = sys.argv[i+1]
                sbl_path = sbl_path.strip()
                if not os.path.exists(sbl_path) or sbl_path.split('.')[-1] != 'bin':
                    print("Error: Please specify a path to a .bin file")
                    sys.exit(1)
            elif sys.argv[i] == "-pcl":
                enbl_pcl = True
            elif sys.argv[i] == "-baud":
                serial_baud = int(sys.argv[i+1])
            elif (sys.argv[i] == "-h") or (sys.argv[i] == "--help"):
                print(help_str)
                sys.exit(0)

    if enbl_pcl and (new_firmware or new_param_config or new_comm_config or new_sbl):
        print("Error: updates are not supported in point cloud mode")
        sys.exit(1)
    '''
    Start user-defined code block.
    User should initialize necessary variables, etc. here.
    User must assign their callback function defined above
    to the callback variable. The callback will be called every
    time a message is received from the radar. It will also call
    the API's to update firmware, communication paramters, and/or
    radar parameters.
    '''

    targ_callback = my_target_callback
    pcl_callback = my_pcl_callback

    '''
    End user-defined code block
    '''
    # Set up an event loop to make the python interpreter run periodically
    # so that ctrl+c will disconnect the radar and kill the program
    signal.signal(signal.SIGINT, sigint_handler)

    #Run supervisor on same timer as before to initialize necessary 
    #config lists, firmware updates, etc

    wayv_air = Wayv_Air_API(targ_callback, radar_con_callback, pcl_callback,
                            (v_level >= 3), comm_mode, serial_port, serial_baud,
                            rs485_id, wifi_ip, target_detail, wifi_port)
                            
    timer = threading.Timer(2,supervisor)
    timer.start()
    if v_level >= 1:
        print("WAYV Air API version:", wayv_air.version)
    wayv_air.radar_connect()
    time.sleep(2)  # delay long enough for the radar to connect over WiFi

    #Initialize signal watcher for config 
    smokesignal.on('config_ready',supervisor)
    #Join the receiver thread to main thread for better handling of ctrl+c signal
    wayv_air.receiver.join()