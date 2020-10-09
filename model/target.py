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
import math


class Target(object):
    def __init__(self, tid=0, x=0.0, y=0.0, z=0.0):
        # id
        self.tid = tid
        # 坐标
        self.x = x
        self.y = y
        self.z = z


class TestTarget(object):
    def __init__(self):
        #
        self.power_real_list = []
        self.power_imaginary_list = []
        self.power_list = []
        self.dis_list = []
        self.doppler_list = []
        self.noise1_list = []
        self.noise2_list = []
        self.noise3_list = []
        self.sub_list = []

    def calc_power(self):
        for i in range(len(self.power_real_list)):
            power = (math.log10(math.sqrt(self.power_real_list[i] ** 2 + self.power_imaginary_list[i] ** 2)))*20
            self.power_list.append(power)


class DebugTarget(object):
    def __init__(self, tid=0, x=0.0, y=0.0, z=0.0, vel_x=0.0, vel_y=0.0, vel_z=0.0, a_x=0.0, a_y=0.0, a_z=0.0,
                 cp_count=0, is_target_static=0, thre=0, active2_free_count=0):
        # id
        self.tid = tid
        # 坐标
        self.x = x
        self.y = y
        self.z = z
        #
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.vel_z = vel_z
        #
        self.a_x = a_x
        self.a_y = a_y
        self.a_z = a_z
        #
        self.cp_count = cp_count
        self.is_target_static = is_target_static
        #
        self.thre = thre
        self.active2_free_count = active2_free_count

class DetailTarget(object):
    def __init__(self, tid=0, x=0.0, y=0.0, z=0.0, vel_x=0.0, vel_y=0.0, vel_z=0.0, a_x=0.0, a_y=0.0, a_z=0.0,
                 cp_count=0):
        # id
        self.tid = tid
        # 坐标
        self.x = x
        self.y = y
        self.z = z
        #
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.vel_z = vel_z
        #
        self.a_x = a_x
        self.a_y = a_y
        self.a_z = a_z
        #
        self.cp_count = cp_count

class TLVCloudPoint(object):
    def __init__(self, range, azimuth, elevation, doppler, snr):
        self.range = range
        self.azimuth = azimuth
        self.elevation = elevation
        self.doppler = doppler
        self.snr = snr


class TLVTargetPoint(object):
    def __init__(self, tid, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, dim_x, dim_y, dim_z, cp_count, is_target_static,
                 thre=0, active2_free_count=0):
        self.tid = tid
        self.posX = pos_x
        self.posY = pos_y
        self.posZ = pos_z
        self.velX = vel_x
        self.velY = vel_y
        self.velZ = vel_z
        self.dimX = dim_x
        self.dimY = dim_y
        self.dimZ = dim_z
        self.cp_count = cp_count
        self.is_target_static = is_target_static
        self.thre = thre
        self.active2_free_count = active2_free_count


class TLVTargrtIndex(object):
    def __init__(self, target_id):
        self.target_id = target_id
