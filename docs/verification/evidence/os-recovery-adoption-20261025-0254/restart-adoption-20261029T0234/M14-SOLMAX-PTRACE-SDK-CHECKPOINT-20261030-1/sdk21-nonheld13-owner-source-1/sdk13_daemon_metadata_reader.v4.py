#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact root-only read of retained daemon identity; no daemon mutation or Docker query.
"""
import json,os,stat,sys
from pathlib import Path

PID=2036
BIRTH=1513
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
SOCKET='/var/run/docker.sock'

def proc_identity(pid):
    raw=Path('/proc',str(pid),'stat').read_text()
    if len(raw)>65536:raise ValueError('oversized stat')
    fields=raw.rsplit(')',1)[1].split()
    return {'pid':pid,'birth':int(fields[19]),'ppid':int(fields[1]),'pgid':int(fields[2]),'sid':int(fields[3])}

def sample():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('root CPU7 required')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('boot identity mismatch')
    before=proc_identity(PID)
    if before['birth']!=BIRTH:raise ValueError('daemon birth mismatch before sample')
    exe=os.stat('/proc/%d/exe'%PID);sock=os.stat(SOCKET)
    after=proc_identity(PID)
    if after['birth']!=before['birth'] or after['birth']!=BIRTH:raise ValueError('daemon birth drift')
    if not stat.S_ISREG(exe.st_mode) or not stat.S_ISSOCK(sock.st_mode):raise ValueError('daemon exe/socket type mismatch')
    return {'status':'OBSERVED_EXACT_DAEMON_READONLY',
            'daemon':{'pid':PID,'starttime':BIRTH,'exe_device':exe.st_dev,'exe_inode':exe.st_ino,
                      'socket_device':sock.st_dev,'socket_inode':sock.st_ino},
            'daemon_birth_before':before['birth'],'daemon_birth_after':after['birth'],
            'boot_id':BOOT,'reader':proc_identity(os.getpid()),'current_free':False}

if __name__=='__main__':
    try: print(json.dumps(sample(),sort_keys=True),flush=True)
    except BaseException as exc:
        print(json.dumps({'status':'UNKNOWN_DAEMON_READ','error':type(exc).__name__+': '+str(exc),
                          'current_free':False},sort_keys=True),flush=True);sys.exit(2)
