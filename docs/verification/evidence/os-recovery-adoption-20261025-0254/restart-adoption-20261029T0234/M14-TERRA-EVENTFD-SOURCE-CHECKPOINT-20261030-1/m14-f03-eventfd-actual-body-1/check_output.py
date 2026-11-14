#!/usr/bin/env python3
"""Independent byte oracle for captured functional eventfd mocks; no native transport."""
from pathlib import Path
import struct
p=Path(__file__).parent; c=(p/'command-3.stdout').read_bytes();r=(p/'command-4.stdout').read_bytes();assert c==r
rows=c.decode('ascii').splitlines();assert len(rows)==9
pairs=[(v,ret) for v in (0,-7,2**31-1) for ret in (0,-11,5)]
for line,(val,ret) in zip(rows,pairs):
 a=line.split();assert len(a)==7
 assert list(map(int,a[:6]))==[val,ret,0,0x1234,0,1]
 expected=bytearray(128);struct.pack_into('<i',expected,8,0x46);struct.pack_into('<i',expected,24,val)
 assert bytes.fromhex(a[6])==expected
print('PASS 9 independent complete 128-byte packet, channel, CPU, option and call-count checks')
