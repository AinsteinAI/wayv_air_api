# -*- coding: utf-8 -*-
import unittest
from worker.msg.msg_detail import *
from worker.msg.msg_485 import *
from worker.msg.msg_jzq import *


class TestMsgFunc(unittest.TestCase):

    def test_msg_send(self):
        msg_485 = Msg485Send(1)
        msg_485_bytes = msg_485.get_cmd(CMD_485_VERSION, bytes())
        self.assertEqual(msg_485_bytes,
                         b'\xff\xff\xff\xff\x10\x26\x02\xc1\x0c\x00\x00\x00\x40\x12\x01\x00\x00\x00\x00\x00\x00\x00')

        msg_jzq = MsgJZQSend(1)
        msg_jzq.set_data(msg_485_bytes)
        msg_jzq_bytes = msg_jzq.get_bytes()
        self.assertEqual(msg_jzq_bytes,
                         b'\x55\xaa\x01\x16\x00\xff\xff\xff\xff\x10\x26\x02\xc1\x0c\x00\x00\x00\x40\x12\x01\x00\x00'
                         b'\x00\x00\x00\x00\x00\x40\x54\xaa\x55')

    def test_msg_recv(self):
        msg_jzq_bytes = b'\x55\xaa\x02\x16\x00\xff\xff\xff\xff\x96\xf7\x02\xc1\x0c\x00\x00\x00\xc0\x10\x01\x00' \
                        b'\x00\x00\xaa\x21\xcb\x55\x0e\x2a\xaa\x55'
        left_bytes, msgs_jzq = MsgJZQRecv.parse_data(msg_jzq_bytes)
        self.assertEqual(len(left_bytes), 0)
        self.assertEqual(len(msgs_jzq), 1)
        msg_jzq = msgs_jzq[0]
        self.assertEqual(msg_jzq.id_line, 2)

        left_bytes, msgs_485 = Msg485Recv.parse_data(msg_jzq.data)
        self.assertEqual(len(left_bytes), 0)
        self.assertEqual(len(msgs_485), 1)


if __name__ == '__main__':
    unittest.main()
