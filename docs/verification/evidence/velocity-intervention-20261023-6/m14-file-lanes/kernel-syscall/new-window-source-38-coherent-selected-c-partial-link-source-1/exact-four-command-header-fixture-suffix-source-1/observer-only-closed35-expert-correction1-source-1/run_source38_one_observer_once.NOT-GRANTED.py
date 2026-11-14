#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One finite reviewed ordinary Source38 sequence. No grant is implied by preparation.
"""
import ast
import builtins
import datetime
import dis
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
SPEC = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-38-coherent-selected-c-partial-link-source-1/exact-one-observer-header-fixture-suffix-source-1/observer-only-closed35-expert-correction1-source-1/EXACT-SOURCE38-ONE-OBSERVER-ENVELOPE.SOURCE-ONLY.json', 'bytes': 88099, 'sha256': 'def9323980e53b3171c57ddc2af6f0eda92989eaffbd56f844bfce07ecda860c'}
RECIPE = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-38-coherent-selected-c-partial-link-source-1/exact-one-observer-header-fixture-suffix-source-1/observer-only-closed35-expert-correction1-source-1/EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json', 'bytes': 95205, 'sha256': 'c9b816e8f915a75007dfc42e4ccd0370accb0c2f0398610497a2b20e58be4b9d'}
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
GRANT = HERE / 'ROOT-EXACT-SOURCE38-ONE-OBSERVER-GRANT.json'
CAPTURE = HERE / 'actual-one-observer-capture-1'
RESULT = HERE / 'ACTUAL-SOURCE38-ONE-OBSERVER-FIRST-RESULT.json'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
FIELDS = ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
MAXIMUM_FILE = 32 << 20

def need(condition,message):
    if not condition:
        raise RuntimeError(message)

def write(path,value):
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def stamp():
    return dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic_seconds=time.monotonic())

def identity(value):
    return {key:getattr(value,key) for key in FIELDS}

def snapshot(path,fd,lexical_before=None):
    path = Path(path)
    lexical_before = path.lstat() if lexical_before is None else lexical_before
    before = os.fstat(fd)
    need(stat.S_ISREG(before.st_mode) and before.st_nlink >= 1 and before.st_size <= MAXIMUM_FILE,'bounded regular input required: '+str(path))
    need(not os.get_inheritable(fd),'input FD must be CLOEXEC')
    os.lseek(fd,0,os.SEEK_SET)
    digest,size = hashlib.sha256(),0
    while True:
        block = os.read(fd,65536)
        if not block:
            break
        size += len(block)
        need(size <= MAXIMUM_FILE,'input grew beyond bound')
        digest.update(block)
    after,target,lexical_after = os.fstat(fd),path.stat(),path.lstat()
    need(identity(before)==identity(after)==identity(target) and identity(lexical_before)==identity(lexical_after) and size==before.st_size,'held FD/path metadata changed: '+str(path))
    return dict(path=str(path),bytes=size,sha256=digest.hexdigest(),target_identity=identity(before),lexical_identity=identity(lexical_after),CLOEXEC=True)

def open_snapshot(path):
    path = Path(path)
    lexical = path.lstat()
    fd = os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        return fd,snapshot(path,fd,lexical)
    except BaseException:
        os.close(fd)
        raise

def byte_pin(path):
    fd,row = open_snapshot(path)
    try:
        return {key:row[key] for key in ('path','bytes','sha256')}
    finally:
        os.close(fd)

def dependencies(code):
    result = {item.argval for item in dis.get_instructions(code) if item.opname=='LOAD_GLOBAL'}
    for child in code.co_consts:
        if isinstance(child,type(code)):
            result.update(dependencies(child))
    return result

def main():
    started = time.monotonic()
    records,continuous,baseline,namespace = [],{},None,{}
    timer_started = False
    peak_FDs = 0
    try:
        need(time.time()+96 <= 1793030133,'same fixed window has insufficient bounded time')
        need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7},'ordinary UID1000 control CPU7 required')
        need(byte_pin(SPEC['path'])==SPEC and byte_pin(RECIPE['path'])==RECIPE,'frozen source spec/recipe changed')
        spec = json.loads(Path(SPEC['path']).read_text())
        recipe = json.loads(Path(RECIPE['path']).read_text())
        output = Path(recipe['fresh_output_root'])
        need(all(not os.path.lexists(path) for path in (output,CAPTURE,RESULT)),'fresh output/capture/result required; no replay')
        need(len(recipe['commands'])==1 and all(command['expected_returncode']==0 for command in recipe['commands']),'exact one positive commands required')
        own_pin = byte_pin(Path(__file__).resolve())
        grant = json.loads(GRANT.read_text())
        authority = grant.get('root_grant')
        need(isinstance(authority,dict) and authority.get('authority')=='/root' and authority.get('authorized') is True and authority.get('once') is True
             and grant.get('runner')==own_pin and grant.get('recipe')==RECIPE and grant.get('spec')==SPEC and grant.get('profile')==spec['profile'],
             'separate exact non-NULL durable Root grant required')
        raw = HELPER.read_bytes()
        need(hashlib.sha256(raw).hexdigest()==HELPER_SHA,'reviewed h990 source changed')
        functions = {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
        assignments = {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
        nodes = [node for node in ast.parse(raw).body if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in functions or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in assignments for target in node.targets)]
        namespace = {'__file__':str(HELPER)}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),namespace)
        used = set().union(*(dependencies(namespace[name].__code__) for name in functions))
        need(not used-set(namespace)-set(vars(builtins)),'h990 extraction dependency missing')
        extra = [RECIPE,SPEC,spec['input_map'],spec['source_READY'],spec['source_manifest'],own_pin,byte_pin(GRANT),byte_pin(HELPER),dict(path=str(namespace['CENSUS_SOURCE']),bytes=namespace['CENSUS_SOURCE'].stat().st_size,sha256=namespace['CENSUS_SHA'])]
        expected = {}
        for row in recipe['pinned_inputs']+extra:
            need(set(row)=={'path','bytes','sha256'},'exact byte binding shape required')
            need(row['path'] not in expected or expected[row['path']]==row,'conflicting input binding')
            expected[row['path']] = row
        critical_paths = {row['path'] for row in spec['critical_recipe_inputs']}|{row['path'] for row in extra}
        header_paths = [row['path'] for row in spec['batched_header_inputs'] if row['path'] not in critical_paths]
        need(set(expected)==critical_paths|set(header_paths),'complete exact input partition required')
        policy = spec['held_FD_policy']
        need(len(critical_paths)<=policy['continuous_limit']==64 and policy['header_batch']==24 and policy['FD_capture_reserve']==32,'finite FD plan changed')
        need(len(os.listdir('/proc/self/fd'))+len(critical_paths)+24+32<256,'FD256 cannot admit held inputs and capture reserve')
        initial = {}
        for path in sorted(critical_paths):
            fd,row = open_snapshot(path)
            continuous[path] = fd
            need({key:row[key] for key in ('path','bytes','sha256')}==expected[path],'critical byte binding changed: '+path)
            initial[path] = row
        peak_FDs = len(os.listdir('/proc/self/fd'))
        baseline = dict(initial)
        def verify():
            nonlocal peak_FDs
            observed = {}
            for path,fd in continuous.items():
                row = snapshot(path,fd)
                need(row==baseline[path],'continuous input identity changed: '+path)
                observed[path] = row
            for index in range(0,len(header_paths),24):
                opened = []
                try:
                    for path in header_paths[index:index+24]:
                        fd,row = open_snapshot(path)
                        opened.append(fd)
                        need({key:row[key] for key in ('path','bytes','sha256')}==expected[path],'header byte binding changed: '+path)
                        if path in baseline:
                            need(row==baseline[path],'header identity changed across sequence: '+path)
                        else:
                            baseline[path] = row
                        observed[path] = row
                    peak_FDs = max(peak_FDs,len(os.listdir('/proc/self/fd')))
                    need(peak_FDs+32<256,'FD capture reserve exhausted')
                finally:
                    for fd in reversed(opened):
                        os.close(fd)
            need(set(observed)==set(expected),'input coverage incomplete')
            return [observed[path] for path in sorted(observed)]
        admitted = verify()
        mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        host,scratch = os.statvfs('/home/holden'),os.statvfs('/home/holden/mckernel-work/scratch')
        need(os.environ.get('MCKERNEL_OS_MEMORY_GIB')=='22.0485' and mem>=25501368320
             and host.f_bavail*host.f_frsize>=(16<<30)+(64<<20) and scratch.f_bavail*scratch.f_frsize>=12<<30,'existing ordinary resource floors')
        os.environ.update(RUST_MIN_STACK='2097152',LC_ALL='C',OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        for number in namespace['STOP_SIGNALS']:
            signal.signal(number,namespace['stop'])
        for key,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_STACK,2<<20),(resource.RLIMIT_CORE,0)]:
            resource.setrlimit(key,(value,value))
        output.mkdir(mode=0o700)
        CAPTURE.mkdir(mode=0o700)
        write(CAPTURE/'profile-and-admission.json',dict(scope=SCOPE,profile=spec['profile'],FD_policy=policy,continuously_held_inputs=len(continuous),batched_headers=len(header_paths),admitted_inputs=admitted,maximum_open_FDs=peak_FDs,MemAvailable_bytes=mem,host_available_bytes=host.f_bavail*host.f_frsize,scratch_available_bytes=scratch.f_bavail*scratch.f_frsize,recipe=RECIPE,spec=SPEC,grant=byte_pin(GRANT),**stamp()))
        signal.setitimer(signal.ITIMER_REAL,max(0.1,96-(time.monotonic()-started)))
        timer_started = True
        for index,command in enumerate(recipe['commands']):
            inputs_before = verify()
            remaining_wall = 90-(time.monotonic()-started)
            remaining_CPU = int(60-namespace['cpu_used']())
            need(remaining_wall>0 and remaining_CPU>=1,'whole ordinary CPU/wall budget exhausted')
            capture = CAPTURE/('%02d'%index)
            capture.mkdir(mode=0o700)
            write(capture/'frozen-command-and-inputs.json',dict(command=command,inputs=inputs_before,**stamp()))
            write(capture/'enqueue-observation.json',dict(argv=command['argv'],parent_affinity=sorted(os.sched_getaffinity(0)),CPU_seconds=namespace['cpu_used'](),**stamp()))
            def limits():
                os.sched_setaffinity(0,{0})
                os.chdir(command['cwd'])
                resource.setrlimit(resource.RLIMIT_CPU,(remaining_CPU,remaining_CPU))
            def started_reader(pid):
                birth = namespace['process_start'](pid)
                affinity = sorted(os.sched_getaffinity(pid))
                write(capture/'start-observation.json',dict(pid=pid,start=birth,command_affinity=affinity,compiler_driver=command['argv'][0]=='/usr/bin/gcc-9',observed_argv0=command['argv'][0],**stamp()))
                need(affinity==[0],'command did not enter CPU0')
                return birth
            joined = namespace['owned_capture'](command,capture,remaining_wall,limits,started_reader=started_reader)
            write(capture/'whole-join-and-end.json',dict(join=joined,CPU_seconds=namespace['cpu_used'](),maximum_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,**stamp()))
            records.append(dict(command=command,join=joined))
            write(capture/'post-command-inputs.json',dict(inputs=verify(),**stamp()))
            need(joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error'] and not joined['timed_out'],'first unexpected result; STOP preserve prefix, no retry')
        need(namespace['cpu_used']()<=60,'whole CPU budget exceeded')
        final = verify()
        outputs = [byte_pin(Path(recipe['retained_output_root'])/name) for name in ('syscall.selected.o','syscall.selected.d','coherent-selected.partial.o')]
        outputs += [byte_pin(recipe['retained_process']['path']),byte_pin(recipe['retained_process_dependencies']['path'])]
        report = Path(RECIPE['path']).parent/'ACTUAL-SOURCE38-SELECTED-C-PARTIAL-OWNERSHIP.json'
        need(json.loads(report.read_text())['status']=='PASS_SOURCE38_SELECTED_C_ABI_AND_COHERENT_PARTIAL_OWNERSHIP_ONLY','strict ownership result missing')
        write(RESULT,dict(scope=SCOPE,status='PASS_SOURCE38_ONE_OBSERVER_SELECTED_C_ABI_AND_COHERENT_PARTIAL_ONLY',records=records,seconds=time.monotonic()-started,CPU_seconds=namespace['cpu_used'](),maximum_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,maximum_open_FDs=peak_FDs,FD_policy=policy,final_inputs=final,actual_outputs=outputs,strict_report=byte_pin(report),recipe=RECIPE,spec=SPEC,root_grant=byte_pin(GRANT),CPU0_released=True,Rust_compiler_replays=0,CPU_VM_ASM_replays=0,canonical_mutations=0,default_image=False,native=False))
        print(json.dumps(dict(status='PASS_SOURCE38_ONE_OBSERVER_SELECTED_C_ABI_AND_COHERENT_PARTIAL_ONLY',result=byte_pin(RESULT))))
        return 0
    except BaseException as error:
        value = dict(scope=SCOPE,status='FAIL_STOP_PRESERVE_PREFIX_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,seconds=time.monotonic()-started,CPU_seconds=namespace['cpu_used']() if 'cpu_used' in namespace else None,maximum_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,maximum_open_FDs=peak_FDs,CPU0_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records),canonical_mutations=0,native=False,default_image=False)
        if not RESULT.exists():
            write(RESULT,value)
        raise
    finally:
        if timer_started:
            signal.setitimer(signal.ITIMER_REAL,0)
        for fd in reversed(list(continuous.values())):
            os.close(fd)

if __name__=='__main__':
    sys.exit(main())
