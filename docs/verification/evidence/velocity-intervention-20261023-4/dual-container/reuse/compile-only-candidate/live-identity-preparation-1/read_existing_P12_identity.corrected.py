"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact read-only identity bootstrap for existing compile-only admission. No lifecycle/lease/control action.
"""
import ast,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def birth(pid):
    assert type(pid) is int and pid > 1
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    return int(fields[19])

assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7} and sys.version_info[:3]==(3,9,12)
NAME='/mckernel-native-diagnostic-b7d8049b46414a86a4fd2b320ba85a62';NONCE='b7d8049b46414a86a4fd2b320ba85a62'
EXPECTED_OWNER=3951805;EXPECTED_OWNER_BIRTH=59198725
EXPECTED_OUTER=3951801;EXPECTED_OUTER_BIRTH=59198713
assert birth(EXPECTED_OWNER)==EXPECTED_OWNER_BIRTH and birth(EXPECTED_OUTER)==EXPECTED_OUTER_BIRTH
argv=['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect',NAME[1:]]
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
helper_raw = HELPER.read_bytes()
assert hashlib.sha256(helper_raw).hexdigest() == HELPER_SHA
functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
body = []
for node in ast.parse(helper_raw, str(HELPER)).body:
    if isinstance(node, (ast.Import, ast.ImportFrom)) or isinstance(node, ast.FunctionDef) and node.name in functions or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
        body.append(node)
ns = {'__file__': str(HELPER)}
exec(compile(ast.Module(body=body, type_ignores=[]), str(HELPER), 'exec'), ns)
for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(signum, ns['stop'])
capture=Path(__file__).resolve().parent/'actual-live-identity-bootstrap-1'
capture.mkdir(mode=0o700)
command={'purpose':__doc__,'argv':argv}
ns['write'](capture/'command.json',command)
def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (33554432, 33554432))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
result=ns['owned_capture'](command,capture,30,limits)
ns['write'](capture/'whole-join.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams']
assert result['error'] is None and result['retirement_error'] is None
stdout=capture/'stdout';stderr=capture/'stderr'
assert stdout.stat().st_size<=4*2**20 and stderr.stat().st_size==0
inspect_raw=stdout.read_bytes()
assert len(inspect_raw)<=4*2**20
rows=json.loads(inspect_raw);assert isinstance(rows,list) and len(rows)==1
r=rows[0];assert r['Name']==NAME and len(r['Id'])==64 and all(v in '0123456789abcdef' for v in r['Id'])
assert r['Config']['Labels']['mckernel.native-diagnostic.owner']==NONCE and r['State']['Running'] is True
pid=r['State']['Pid'];assert type(pid) is int and pid>1
first=birth(pid)
cgroups=(Path('/proc')/str(pid)/'cgroup').read_bytes();assert len(cgroups)<=65536
cg_expected={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us': '100000', '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us': '400000', '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes': '12884901888', '/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy': '1', '/sys/fs/cgroup/pids/mckernel-dev/pids.max': '512'}
cg_actual={path:Path(path).read_text().strip() for path in cg_expected}
assert cg_actual==cg_expected and birth(pid)==first and birth(EXPECTED_OWNER)==EXPECTED_OWNER_BIRTH and birth(EXPECTED_OUTER)==EXPECTED_OUTER_BIRTH
print(json.dumps(dict(scope=__doc__,status='READONLY_CURRENT_P12_CONTAINER_IDENTITY_BOOTSTRAP_NOT_ADMISSION',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),nonce=NONCE,owner={'pid':EXPECTED_OWNER,'starttime':EXPECTED_OWNER_BIRTH},outer={'pid':EXPECTED_OUTER,'starttime':EXPECTED_OUTER_BIRTH},container_init={'pid':pid,'starttime':first},P12={'id':r['Id'],'name':r['Name'],'owner_label_key':'mckernel.native-diagnostic.owner','owner_label_value':NONCE,'config_sha256':canonical(r['Config']),'host_config_sha256':canonical(r['HostConfig'])},P12_rw_roots=sorted(set(m['Source'] for m in r['Mounts'] if m.get('RW') is True and m.get('Source','').startswith('/'))),inspect=r,inspect_raw_sha256=hashlib.sha256(inspect_raw).hexdigest(),init_cgroup=cgroups.decode(),cgroup_facts=cg_actual,observed_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),compile_admission=False,compiler_release=False,mutations=0,signals=0),sort_keys=True))
