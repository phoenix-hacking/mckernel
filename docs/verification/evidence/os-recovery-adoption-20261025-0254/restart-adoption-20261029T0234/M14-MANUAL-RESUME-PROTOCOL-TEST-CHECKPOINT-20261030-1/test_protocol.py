"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic checks only; do not execute without reviewed admission.
"""
import socket
import struct
import unittest
from unittest.mock import patch
import custody_protocol_v2 as wire
import graph_observations as graph


class WireFixture(unittest.TestCase):
    def test_round_trip(self):
        left,right=socket.socketpair()
        try:
            deadline=wire.boot_now()+1
            expected=wire.envelope('union','union-lease-check','1'*64,1,'2'*64,'3'*64,{'observation':{}})
            wire.send(left,expected,deadline)
            got=wire.receive(right,deadline)
            self.assertEqual(wire.validate(got,'union','union-lease-check','1'*64,1,'2'*64,'3'*64),{'observation':{}})
        finally:
            left.close();right.close()

    def test_wrong_nonce_sequence_and_endpoint_rejected(self):
        got=wire.envelope('union','union-lease-check','1'*64,1,'2'*64,'3'*64,None)
        for args in [('union','union-lease-check','0'*64,1),('union','union-lease-check','1'*64,2),('graph','union-lease-check','1'*64,1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                wire.validate(got,*args,'2'*64,'3'*64)
        with self.assertRaises(ValueError): wire.envelope('union','x','1'*32,1,'2'*64,'3'*64,None)

    def test_boolean_and_float_identity_fields_rejected(self):
        for key,value in [('version',True),('version',1.0),('seq',True),('seq',1.0)]:
            item=wire.envelope('union','union-lease-check','1'*64,1,'2'*64,'3'*64,None)
            item[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                wire.validate(item,'union','union-lease-check','1'*64,1,'2'*64,'3'*64)

    def test_duplicate_keys_rejected(self):
        left,right=socket.socketpair()
        try:
            raw=b'{"nonce":1,"nonce":2}'
            left.sendall(struct.pack('!I',len(raw))+raw)
            with self.assertRaises(ValueError):wire.receive(right,wire.boot_now()+1)
        finally:
            left.close();right.close()

    def test_partial_progress_does_not_extend_deadline(self):
        left,right=socket.socketpair()
        try:
            left.sendall(struct.pack('!I',10)+b'a')
            # Peer remains open but does not supply the rest of the frame.
            with self.assertRaises(TimeoutError):wire.receive(right,wire.boot_now()+0.05)
        finally:
            left.close();right.close()

    def test_mountinfo_escapes(self):
        self.assertEqual(graph.decode_path(r'/a\040b\134c'),'/a b\\c')
        with self.assertRaises(ValueError):graph.decode_path(r'/a\377')
        with self.assertRaises(ValueError):graph.decode_path(r'/a\x')


if __name__=='__main__':unittest.main()
