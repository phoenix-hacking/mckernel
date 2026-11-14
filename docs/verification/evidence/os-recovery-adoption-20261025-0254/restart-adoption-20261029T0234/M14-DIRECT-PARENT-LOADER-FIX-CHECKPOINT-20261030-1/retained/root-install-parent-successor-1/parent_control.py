"""Functional install-only root-parent/keeper FD custody protocol; source only."""
import array
import json
import os
import select
import socket
import struct
import time
import deferred_fork

MAX_FRAME=131072
MAX_FDS=8
CRED=struct.Struct('3i')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate key')
        out[key]=value
    return out


def remaining(caps):
    return min(caps['boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME),
               caps['mono_ns']-time.monotonic_ns(),caps['utc_ns']-time.time_ns())


def wait(sock,events,caps):
    poll=select.poll();poll.register(sock.fileno(),events|select.POLLERR|select.POLLHUP)
    while True:
        left=remaining(caps)
        if left<=0:raise TimeoutError('absolute operation cap')
        try:result=poll.poll(min(100,max(1,left//1000000)))
        except InterruptedError:continue
        if result:
            mask=result[0][1]
            if mask&(select.POLLERR|select.POLLNVAL):raise OSError('control channel error')
            if mask&events:return
            if mask&select.POLLHUP:raise EOFError('control channel lost')


def send(sock,message,fds,caps):
    raw=canonical(message)
    if len(raw)>MAX_FRAME or len(fds)>MAX_FDS:raise ValueError('frame bounds')
    ancillary=[] if not fds else [(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',fds))]
    wait(sock,select.POLLOUT,caps)
    sent=sock.sendmsg([raw],ancillary,socket.MSG_DONTWAIT)
    if sent!=len(raw):raise OSError('short seqpacket')


class ReceivedCustody:
    def __init__(self):
        self.ancillary=None;self.fds=[];self.state='PENDING_RECEIVE'


def receive(sock,caps,held,expected_pid):
    """Pre-register ownership; defer configured stops until FD registration."""
    wait(sock,select.POLLIN,caps)
    record=ReceivedCustody();held.append(record)
    ancsize=socket.CMSG_SPACE(MAX_FDS*array.array('i').itemsize)+socket.CMSG_SPACE(CRED.size)
    with deferred_fork.DeferredFork():
        raw,ancillary,flags,_=sock.recvmsg(MAX_FRAME+1,ancsize,socket.MSG_CMSG_CLOEXEC|socket.MSG_DONTWAIT)
        record.ancillary=ancillary
        fds=[];creds=[];bad=False
        for level,kind,payload in ancillary:
            if level!=socket.SOL_SOCKET:bad=True;continue
            if kind==socket.SCM_RIGHTS:
                a=array.array('i');usable=len(payload)-len(payload)%a.itemsize
                a.frombytes(payload[:usable]);record.fds.extend(a);fds.extend(a)
                if usable!=len(payload):bad=True
            elif kind==socket.SCM_CREDENTIALS and len(payload)==CRED.size:creds.append(CRED.unpack(payload))
            else:bad=True
        record.state='RECEIVED_RETAINED'
    if (flags&(socket.MSG_TRUNC|socket.MSG_CTRUNC) or bad or len(fds)>MAX_FDS or
        len(raw)>MAX_FRAME or not raw.endswith(b'\n') or len(creds)!=1 or
        creds[0][0]!=expected_pid or creds[0][1]!=0):raise ValueError('frame/credentials unknown; received FDs retained')
    value=json.loads(raw,object_pairs_hook=unique)
    if type(value) is not dict or canonical(value)!=raw:raise ValueError('noncanonical frame')
    return value,fds
