"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed exact read-only Root70 identity observation. NOT an execution release.
"""
import ast,hashlib,json,os,resource,signal,stat,subprocess,sys,time
from pathlib import Path

CID='a7fe0b67d129afc3868d329d65f68317b6aadee6bedd7bc76330a52cdd0ae7ef'
EXPECTED_NAME='/conversion-first-build-only-4709c9fae2c743a7acd662e93a663358'
IMAGE='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
PROFILE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld12-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json')
PROFILE_SHA='c88825ef2e2cfbf28e8e244c2010748c493bdb0924fc333a69b79eb80d627d69'
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
CAPTURE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-root70-readonly-admission-source-1/root70-observation-1')
HOST=Path('/home/holden/mckernel-work'); SCRATCH=Path('/home/holden/mckernel-work/scratch')
FORMAT='\n'.join('{{json '+x+'}}' for x in ('.Id','.Name','.Image','.State.Running','.State.Status','.State.Pid','.State.Paused','.State.Restarting','.State.Dead','.HostConfig.CpusetCpus','.HostConfig.Memory','.HostConfig.MemorySwap','.HostConfig.PidsLimit','.HostConfig.NetworkMode','.Mounts'))
CONTAINER_QUERY=['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--format',FORMAT,CID]
COMMANDS=[CONTAINER_QUERY,['/usr/bin/docker','--host=unix:///var/run/docker.sock','image','inspect','--format','{{json .Id}}',IMAGE],CONTAINER_QUERY]

def fixed_bytes(path,maximum):
    data=path.read_bytes()
    if len(data)>maximum: raise ValueError('pinned input exceeds bound')
    return data

def birth(pid):
    if type(pid) is not int or pid<=1: raise ValueError('invalid process identity')
    raw=Path('/proc/%d/stat'%pid).read_text()
    if len(raw)>65536: raise ValueError('proc stat exceeds bound')
    return int(raw.rsplit(')',1)[1].split()[19])

def clock():
    return {'utc_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),'boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)}

def cpu_list(text):
    vals=set()
    for part in text.strip().split(','):
        bounds=part.split('-')
        if len(bounds)==1: lo=hi=int(bounds[0])
        elif len(bounds)==2: lo,hi=map(int,bounds)
        else: raise ValueError('invalid CPU list')
        if lo<0 or hi<lo or hi>4095: raise ValueError('CPU list outside bound')
        vals.update(range(lo,hi+1))
    return sorted(vals)

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def main():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}: raise ValueError('requires root CPU7 observer profile')
    if sys.version_info[:3]!=(3,9,12): raise ValueError('requires pinned Python version')
    profile_raw=fixed_bytes(PROFILE,2<<20)
    if hashlib.sha256(profile_raw).hexdigest()!=PROFILE_SHA: raise ValueError('SDK profile hash mismatch')
    profile=json.loads(profile_raw)
    if profile['image_and_tools']['image_digest']!=IMAGE: raise ValueError('SDK image binding mismatch')
    raw=fixed_bytes(HELPER,2<<20)
    if hashlib.sha256(raw).hexdigest()!=HELPER_SHA: raise ValueError('capture helper mismatch')
    functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
    assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
    nodes=[]
    for node in ast.parse(raw,str(HELPER)).body:
        if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in functions or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in node.targets):nodes.append(node)
    ns={'__file__':str(HELPER)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),ns)
    # Retain no inherited account, askpass, loader or Docker configuration in the child.
    os.environ.clear();os.environ.update({'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C'})
    for num in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(num,ns['stop'])
    signal.setitimer(signal.ITIMER_REAL,55)
    CAPTURE.mkdir(mode=0o700)
    me=os.getpid();parent=os.getppid();context={'pid':me,'start':birth(me),'ppid':parent,'parent_start':birth(parent),'pgid':os.getpgrp(),'sid':os.getsid(0),'uid':os.getuid(),'euid':os.geteuid(),'affinity':sorted(os.sched_getaffinity(0)),'before':clock()}
    ns['write'](CAPTURE/'context.before.json',context)
    summary={'scope':__doc__,'status':'UNKNOWN_NO_ADMISSION','known_container':CID,'expected_sdk_image':IMAGE,'current_free':False,'no_unlisted_history':'UNKNOWN','physical_release':False,'events':[],'before':context}
    def capture(index):
        path=CAPTURE/('query-%d'%index);path.mkdir(mode=0o700)
        command={'purpose':__doc__,'argv':COMMANDS[index]};ns['write'](path/'command.json',command)
        result=ns['owned_capture'](command,path,20,limits);ns['write'](path/'whole-join.json',result)
        summary['events'].append({'index':index,'join':result})
        if result['returncode']!=0 or not result['direct_child_joined'] or not result['group_absent'] or not result['closed_streams'] or result['error'] or result['retirement_error'] or result['timed_out']:
            raise ValueError('query failed or capture custody UNKNOWN')
        stdout=(path/'stdout').read_bytes();stderr=(path/'stderr').read_bytes()
        if len(stdout)>4<<20 or len(stderr)>2<<20 or stderr: raise ValueError('query capture bounds or stderr')
        return stdout
    try:
        lines=capture(0).decode('utf-8').splitlines()
        if len(lines)!=15:raise ValueError('container inspect output shape')
        v=[json.loads(x) for x in lines]
        if v[0]!=CID or v[1]!=EXPECTED_NAME:raise ValueError('exact container identity or historical owner-name mismatch')
        if not isinstance(v[14],list) or len(v[14])>256:raise ValueError('container mount shape')
        roots=[]
        for m in v[14]:
            if not isinstance(m,dict):raise ValueError('mount object shape')
            if m.get('RW') is True:
                src=m.get('Source');dst=m.get('Destination')
                if not isinstance(src,str) or not src.startswith('/') or not isinstance(dst,str) or not dst.startswith('/'):raise ValueError('writable mount identity unknown')
                roots.append({'source':src,'destination':dst,'type':m.get('Type')})
        summary['container']={'id':v[0],'name':v[1],'image_id':v[2],'running':v[3],'status':v[4],'pid':v[5],'paused':v[6],'restarting':v[7],'dead':v[8],'cpuset':v[9],'memory':v[10],'memory_swap':v[11],'pids_limit':v[12],'network_mode':v[13],'writable_mounts':roots,'image_writable_layer':'NOT_INSPECTED_UNKNOWN'}
        if v[3] is not True or v[4]!='running' or v[6] is not False or v[7] is not False or v[8] is not False:
            summary['status']='OBSERVED_NOT_RUNNING_OR_TRANSITIONAL_STOP_UNKNOWN';return 2
        pid=v[5];start=birth(pid);cg=Path('/proc/%d/cgroup'%pid).read_bytes();ps=Path('/proc/%d/status'%pid).read_text()
        if len(cg)>65536 or len(ps)>131072:raise ValueError('init proc facts exceed bound')
        allowed=[x for x in ps.splitlines() if x.startswith(('Cpus_allowed_list:','Mems_allowed_list:'))]
        if len(allowed)!=2 or birth(pid)!=start:raise ValueError('container init identity drift')
        summary['container_init']={'pid':pid,'start':start,'cgroup':cg.decode('utf-8'),'allowed_lists':allowed,'scope':'exact init only; no all-consumer or history conclusion'}
        if json.loads(capture(1).decode('utf-8'))!=IMAGE or v[2]!=IMAGE:raise ValueError('SDK image identity mismatch')
        memline=[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')]
        if len(memline)!=1 or memline[0].split()[2]!='kB':raise ValueError('meminfo shape')
        mem=int(memline[0].split()[1])*1024
        host=os.statvfs(HOST);scratch=os.statvfs(SCRATCH)
        hostfree=host.f_bavail*host.f_frsize;scratchfree=scratch.f_bavail*scratch.f_frsize
        online=cpu_list(Path('/sys/devices/system/cpu/online').read_text())
        if min(mem,hostfree,scratchfree)<=0:raise ValueError('nonpositive resource facts')
        summary['resource_observation']={'memory_available_bytes':mem,'host_free_bytes':hostfree,'scratch_free_bytes':scratchfree,'host_device':HOST.stat().st_dev,'scratch_device':SCRATCH.stat().st_dev,'cpu_online':online,'CPU6_online':6 in online,'scope':'point-in-time observations only; no exclusive CPU6/resource lease or continuity proof'}
        if mem<24*(1<<30) or hostfree<16*(1<<30) or scratchfree<12*(1<<30) or 6 not in online:raise ValueError('minimum observation not met')
        final_lines=capture(2).decode('utf-8').splitlines()
        if len(final_lines)!=15 or [json.loads(x) for x in final_lines]!=v:raise ValueError('container state or config drift')
        if birth(pid)!=start:raise ValueError('container init changed before final record')
        summary['status']='OBSERVED_BOUNDED_FACTS_NONINTERFERENCE_NOT_ESTABLISHED';return 0
    except BaseException as exc:
        summary['failure']=type(exc).__name__+': '+str(exc);summary['status']='UNKNOWN_STOP_NO_ADMISSION';return 2
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        try:
            summary['after']={'clock':clock(),'self_start':birth(me),'ppid':os.getppid(),'parent_start':birth(parent),'pgid':os.getpgrp(),'sid':os.getsid(0)}
            if summary['after']['self_start']!=context['start'] or summary['after']['ppid']!=parent or summary['after']['parent_start']!=context['parent_start'] or summary['after']['pgid']!=context['pgid'] or summary['after']['sid']!=context['sid']:
                summary['status']='UNKNOWN_CALLER_IDENTITY_DRIFT';summary['failure']='self/parent/group identity drift'
        except BaseException as exc:
            summary['status']='UNKNOWN_CALLER_IDENTITY';summary['failure']='after identity: '+type(exc).__name__+': '+str(exc)
        ns['write'](CAPTURE/'summary.json',summary)
        print(json.dumps({'status':summary['status'],'compile_admission':False,'physical_release':False},sort_keys=True))
        if summary['status']!='OBSERVED_BOUNDED_FACTS_NONINTERFERENCE_NOT_ESTABLISHED':return 2

if __name__=='__main__':
    try:result=main()
    except BaseException as exc:
        print(json.dumps({'status':'UNKNOWN_BEFORE_CAPTURE_OR_UNRECORDED','error':type(exc).__name__+': '+str(exc),'compile_admission':False,'physical_release':False},sort_keys=True),file=sys.stderr);sys.exit(2)
    sys.exit(result)
