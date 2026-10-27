"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
FP composition of accepted N5 read-only admission, using accepted failed Source28 ownership/current-free schema.
No container/guest creation, signal, cleanup, ledger write or resource release.
"""
from pathlib import Path
import argparse,json,os,time,subprocess,hashlib,importlib.util
R=Path(__file__).resolve().parent;A=R.parent;E=A.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-path',required=True,type=Path)
args=parser.parse_args();output=args.output_path
assert output.is_absolute() and output.parent==R,'output must be in exact successor directory'
intermediate_stdout_path=output.with_name(output.stem+'.POSTNATIVE.stdout')
intermediate_stderr_path=output.with_name(output.stem+'.POSTNATIVE.stderr')
# Complete output collision preflight BEFORE any account, clock or query.
for path in [output,intermediate_stdout_path,intermediate_stderr_path]:
 if os.path.lexists(path):raise FileExistsError(str(path))
output_stream=output.open('xb')
intermediate_stdout=intermediate_stdout_path.open('xb')
intermediate_stderr=intermediate_stderr_path.open('xb')

def checked(reference):
 raw=Path(reference['path']).read_bytes()
 assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
 return json.loads(raw)

def ref(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

# BEGIN_UNCHANGED_OBSERVATION_BODY
static=json.loads((R/'STATIC-NATIVE-BINDINGS.RESOURCE-2.NOT-RELEASED.json').read_bytes())
accept=E/'DAEMON-SOURCE28-FAILED-INDEPENDENT-POSTJOIN-CURRENT-ACCEPTANCE.json'
assert static['latest_serial_operation_physical_acceptance']==ref(accept)
d=checked(static['latest_serial_operation_physical_acceptance'])
assert d['decision']=='PASS_FAILED_SOURCE28_DAEMON_OWNED_RETIREMENT_AND_RETAINED_CURRENT_FREE'
assert d['independent'] is True and d['implementation_ownership'] is False and d['reviewer']!='/root'
latest=checked(d['current_observation']);failed=latest['failed_current_daemon_operation']
assert failed['nonce']==d['nonce'] and failed['whole_caller']==d['whole_caller'] and failed['actual_parent_tool']==d['actual_parent_tool']
whole=checked(d['whole_caller']);tool=checked(d['actual_parent_tool'])
assert whole['returncode']==1 and whole['direct_child_joined'] is True and whole['group_absent'] is True and whole['closed_streams'] is True and whole['error'] is None and whole['retirement_error'] is None
assert tool['exit_code']==1 and tool['positive_parent_tool_join'] is True
assert tool['actual_output']['pid']==whole['pid'] and tool['actual_output']['returncode']==whole['returncode'] and tool['actual_output']['direct_child_joined'] is True and tool['actual_output']['group_absent'] is True and tool['actual_output']['closed_streams'] is True
owner=checked(failed['owner_receipt']);post=checked(failed['postflight']);released=checked(failed['record_release_complete']);archive=checked(failed['ownership_archive'])
assert owner['status']=='FAIL' and owner['retired'] is True and owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and owner['cleanup_separately_required'] is False
assert owner['owner_nonce']==d['nonce'] and owner['container_id']==d['container_removed']
assert post['all_clients_reaped'] is True and post['container_absent'] is True and post['absence']['absent'] is True and post['absence']['container_id']==d['container_removed']
assert released['status']=='OWNED_RECORDS_RELEASED' and released['nonce']==d['nonce'] and released['archive_sha256']==failed['ownership_archive']['sha256']
assert archive['nonce']==d['nonce']
client_checks=post['client_group_checks']+post['admission_client_group_checks']
assert all(c['empty'] is True and c['surviving_members']==[] for c in client_checks)
actor_ids={whole['pid']}|{c['pid'] for c in client_checks};assert len(actor_ids)==16
# Preserve the predecessor FIVE retained-exited container and exact actor guards.
five=checked(static['retained_FIVE_physical_acceptance']);five_current=checked(five['actual_current_observation'])
assert five['decision']=='PASS_FIVE_BUILD_POSTJOIN_CURRENT_PHYSICAL' and five['independent'] is True and five['implementation_ownership'] is False
policy=E/'scratch-growth-final-copy-close-source-1/recover_growth_custody.py'
assert hashlib.sha256(policy.read_bytes()).hexdigest()=='04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a'
spec=importlib.util.spec_from_file_location('accepted_actual_account_guard_fp_resource',policy);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());m.check_account_state(state,time.time())
clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
assert all(c<e for c,e in zip(clocks,m.CUTOFFS))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
source=E/'ROOT-CURRENT290-NATIVE-FILES-ADMISSION-1/check_postnative_current.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='66fcc41a7e6c9be22d596efd2a3a19042aace8c351e74e21013b7de357466273'
r=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(source)],capture_output=True,timeout=40)
assert r.returncode==0 and not r.stderr
intermediate_stdout.write(r.stdout);intermediate_stdout.close()
intermediate_stderr.write(r.stderr);intermediate_stderr.close()
current=json.loads(r.stdout)
# Original observer retains prior actors, shared records, exclusive closed probes,
# scratch UUID and capacity floors. Add the latest accepted daemon actors exactly.
for pid in actor_ids|{a['pid'] for a in five_current['retired_births']}:
 assert not Path('/proc',str(pid)).exists()
 assert not any(row['pid']==pid or row['pgrp']==pid for row in current['group_membership_observation']['rows'])
for record in archive['records']:assert not os.path.lexists(record['path'])
# Fresh exact predecessor build remains retained exited0/Pid0, not absent.
inspect_argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect',five['retained_exited_container']]
q=subprocess.run(inspect_argv,capture_output=True,text=True,timeout=15);assert q.returncode==0 and not q.stderr
terminal=json.loads(q.stdout);assert len(terminal)==1 and terminal[0]['Id']==five['retained_exited_container'] and terminal[0]['State']['Running'] is False and terminal[0]['State']['Pid']==0 and terminal[0]['State']['ExitCode']==0
observations=[dict(argv=inspect_argv,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr,positive_wait=True)]
prefix=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','--quiet','--no-trunc']
queries=[prefix,prefix[:5]+['--all']+prefix[5:]+['--filter','id='+d['container_removed']],prefix[:5]+['--all']+prefix[5:]+['--filter','name=^/'+owner['container_name']+'$'],prefix[:5]+['--all']+prefix[5:]+['--filter','label=mckernel.owner='+d['nonce']]]
for argv in queries:
 q=subprocess.run(argv,capture_output=True,text=True,timeout=15);assert q.returncode==0 and not q.stderr and not q.stdout.strip()
 observations.append(dict(argv=argv,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr,positive_wait=True))
observations.insert(0,observations.pop(1))
mem={}
for line in Path('/proc/meminfo').read_text().splitlines():
 k,v=line.split(':',1)
 if k in ['MemTotal','MemAvailable']:mem[k]=int(v.split()[0])*1024
assert mem['MemAvailable']>=24*2**30
paths=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy','/sys/fs/cgroup/pids/mckernel-dev/pids.max']
cgroup={p:Path(p).read_text().strip() for p in paths};assert list(cgroup.values())==['100000','400000','12884901888','1','512']
pids=int(Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text());assert pids==0
result=dict(scope=__doc__.splitlines()[0],observed_clocks=clocks,freshness_seconds_max=120,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),launcher_guard={k:state[k] for k in ['phase','thread_id','heartbeat_at','credit_budget','credit_budget_error','last_rate_limits']},actual_latest_operation_postjoin_acceptance=ref(accept),current_physical_observation=current,no_existing_heavy=True,running_container_observation=observations[0],latest_exact_container_observations=observations[1:],active_shared_records_absent=True,capacity=current['capacity'],memory=mem,cgroup=cgroup,pids_current=pids,container_reservation=dict(cpus='2-5',jobs=4,RAM_bytes=12884901888,pids=512,swap_bytes=0),other_RAM_reserved_bytes=6442450944,aggregate_RAM_ceiling_GiB=21.7531,aggregate_jobs_max=7,fresh_directories=[])
for p in [A/'CAPTURE',Path(static['attempt_parent'])]:
 assert p.is_dir() and not list(p.iterdir());s=p.lstat();result['fresh_directories'].append(dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid))
# END_UNCHANGED_OBSERVATION_BODY
output_stream.write((json.dumps(result,indent=2)+'\n').encode());output_stream.close()
print(json.dumps(dict(retained_resource=ref(output),runtime_authority=None)))
