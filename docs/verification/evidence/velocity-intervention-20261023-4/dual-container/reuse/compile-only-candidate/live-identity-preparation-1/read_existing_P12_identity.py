"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact read-only identity bootstrap for existing compile-only admission. No lifecycle/lease/control action.
"""
import hashlib,json,os,subprocess,sys,time
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
p=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
assert p.returncode==0 and not p.stderr and len(p.stdout)<=4*2**20
rows=json.loads(p.stdout);assert isinstance(rows,list) and len(rows)==1
r=rows[0];assert r['Name']==NAME and len(r['Id'])==64 and all(v in '0123456789abcdef' for v in r['Id'])
assert r['Config']['Labels']['mckernel.native-diagnostic.owner']==NONCE and r['State']['Running'] is True
pid=r['State']['Pid'];assert type(pid) is int and pid>1
first=birth(pid)
cgroups=(Path('/proc')/str(pid)/'cgroup').read_bytes();assert len(cgroups)<=65536
cg_expected={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us': '100000', '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us': '400000', '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes': '12884901888', '/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy': '1', '/sys/fs/cgroup/pids/mckernel-dev/pids.max': '512'}
cg_actual={path:Path(path).read_text().strip() for path in cg_expected}
assert cg_actual==cg_expected and birth(pid)==first and birth(EXPECTED_OWNER)==EXPECTED_OWNER_BIRTH and birth(EXPECTED_OUTER)==EXPECTED_OUTER_BIRTH
print(json.dumps(dict(scope=__doc__,status='READONLY_CURRENT_P12_CONTAINER_IDENTITY_BOOTSTRAP_NOT_ADMISSION',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),nonce=NONCE,owner={'pid':EXPECTED_OWNER,'starttime':EXPECTED_OWNER_BIRTH},outer={'pid':EXPECTED_OUTER,'starttime':EXPECTED_OUTER_BIRTH},container_init={'pid':pid,'starttime':first},P12={'id':r['Id'],'name':r['Name'],'owner_label_key':'mckernel.native-diagnostic.owner','owner_label_value':NONCE,'config_sha256':canonical(r['Config']),'host_config_sha256':canonical(r['HostConfig'])},P12_rw_roots=sorted(set(m['Source'] for m in r['Mounts'] if m.get('RW') is True and m.get('Source','').startswith('/'))),inspect=r,inspect_raw_sha256=hashlib.sha256(p.stdout).hexdigest(),init_cgroup=cgroups.decode(),cgroup_facts=cg_actual,observed_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),compile_admission=False,compiler_release=False,mutations=0,signals=0),sort_keys=True))
