# -*- coding: utf-8 -*-
import crcmod.predefined


class Crc(object):
    @staticmethod
    def calc(data):
        crc16 = crcmod.predefined.Crc("CrcXmodem")
        crc16.update(data)
        return crc16.crcValue
