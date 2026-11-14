# Functional M14 install-only phase zero: exact source literal, reviewed separately.
import hashlib, json, os, stat, sys
BASE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1'
V8=BASE+'/root-install-source-9'
P0=BASE+'/root-install-phase0-v9-source-1/phase0.py'
PRELIM=BASE+'/postjoin-daemon-metadata-observer-source-1/root_parent_preliminary.py'
PHASE_SHA='147c9e17fdbcee498d72bfa42c9630727636a6b3b4ae38fe43618ddf95c4d049'
BOOT_SHA='d91ecd5021e1e0f85311cd86815c23dff6ca8c125c22716fefee23d097b8d8ee'
CLOSURE_SHA='05990d787063e3c8bf5be0153afda5da863397054477cfe2f9b1760f0e212f81'

def load(path, expected):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size>2097152:raise ValueError('bounded source required')
        data=b''
        while len(data)<=2097152:
            chunk=os.read(fd,min(65536,2097153-len(data)))
            if not chunk:break
            data+=chunk
        b=os.fstat(fd)
        if ((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns) or len(data)!=a.st_size or hashlib.sha256(data).hexdigest()!=expected):raise ValueError('source changed')
        return data
    finally:os.close(fd)

def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate admission key')
        out[key]=value
    return out

if len(sys.argv)!=2 or len(sys.argv[1])!=64 or any(c not in '0123456789abcdef' for c in sys.argv[1]):raise ValueError('exact admission digest required')
request_raw=sys.stdin.buffer.read(2097153)
if len(request_raw)>2097152 or hashlib.sha256(request_raw).hexdigest()!=sys.argv[1]:raise ValueError('actual admission bytes differ')
request=json.loads(request_raw,object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
bootstrap=load(V8+'/BOOTSTRAP-CODE.py',BOOT_SHA)
source=load(P0,PHASE_SHA)
closure=load(V8+'/SOURCE-CLOSURE.json',CLOSURE_SHA)
marker=b'intent=opened(intent_path,os.O_RDONLY)'
if bootstrap.count(marker)!=1:raise ValueError('reviewed bootstrap boundary differs')
# Reuse the exact v9 verified-byte loaders and pins, without entering its issuer yet.
sys.argv=['<v9-prelude>',V8+'/install_source_closure.py',V8+'/install_issuer.py',V8+'/install_completion.py',PRELIM,V8+'/WAIT-INSTALL-CODE.py','unused','unused',V8+'/package','unused','unused','unused','unused','unused','unused','unused','unused']
context={'__name__':'__phase0_loader__'}
exec(compile(bootstrap.split(marker,1)[0],'<v9-reviewed-prelude>','exec'),context)
phase={'__name__':'__phase0__'}
exec(compile(source,P0,'exec'),phase)
phase['run'](request,context['install'],context['issuer'],context['prelim'],context['completion'],closure,context['wait_raw'])
