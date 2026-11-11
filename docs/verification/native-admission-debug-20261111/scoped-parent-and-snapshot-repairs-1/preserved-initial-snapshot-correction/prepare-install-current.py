"""Current publication-only adaptation of the retained actual control reader."""
import hashlib
import os
import stat
import time
import types
from datetime import datetime
from pathlib import Path

PRELIM=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-code-package-preparation-sdk-max-1/a2f-fixed30-normal-operation-proposal-1/correction-1/account-snapshot-correction-1/preliminary-current.py')
PRELIM_SHA='509249cd9a272bfe58ecaa12386a6bae0df1573d31b3c18d0f5e96b2c25394f4'
OUTER_PID=762050
OUTER_BIRTH='37669567'


def proc(pid):
    if type(pid) is not int or pid<=1:raise ValueError('process id')
    data=Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
    if len(data)<20 or data[0] in ('Z','X','x'):raise ValueError('process unavailable')
    return {'pid':pid,'ppid':int(data[1]),'birth':data[19]}


def load_prelim():
    fd=os.open(str(PRELIM),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>2*1024*1024:raise ValueError('bounded source')
        raw=b''
        while len(raw)<=2*1024*1024:
            part=os.read(fd,min(65536,2*1024*1024+1-len(raw)))
            if not part:break
            raw+=part
        after=os.fstat(fd)
        if (len(raw)!=before.st_size or len(raw)>2*1024*1024 or
            (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or
            hashlib.sha256(raw).hexdigest()!=PRELIM_SHA):raise ValueError('source binding')
    finally:os.close(fd)
    module=types.ModuleType('_current_publication_prelim');module.__file__=str(PRELIM)
    exec(compile(raw,str(PRELIM),'exec'),module.__dict__)
    return module


def live_controls():
    reader=load_prelim();c,cr=reader.read_bound(reader.CONTROLS,1<<20);p,pr=reader.read_bound(reader.CAPACITY,1<<20)
    controls=reader.strict_json(c);capacity=reader.strict_json(p)
    caps=reader.controller_checks(controls,capacity,time.time())
    usage_raw,_=reader.read_bound(reader.USAGE_EVIDENCE,65536)
    if hashlib.sha256(usage_raw).hexdigest()!=controls.get('usage_sha256'):raise ValueError('usage source changed')
    usage=reader.strict_json(usage_raw)
    observed_ns=int(datetime.fromisoformat(usage['at']).timestamp()*1000000000)
    outer=proc(OUTER_PID)
    if outer['birth']!=OUTER_BIRTH or os.stat('/proc/%d'%OUTER_PID).st_uid!=1000:raise ValueError('actual Root server identity changed')
    return {'controls_sha256':hashlib.sha256(c).hexdigest(),'capacity_sha256':hashlib.sha256(p).hexdigest(),
            'caps':caps,'outer':outer,'controls_data':controls,'capacity_data':capacity,
            'weekly_used_percent':usage['primary']['usedPercent'],'weekly_observed_utc_ns':observed_ns,
            'control_identity':cr,'capacity_identity':pr}
