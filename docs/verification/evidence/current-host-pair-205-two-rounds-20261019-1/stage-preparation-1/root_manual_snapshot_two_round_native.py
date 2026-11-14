"""Case-specific read-only root admission recipe; no owner or guest invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,time
N=Path(__file__).resolve().parent
OUTPUT=N/'root-live-preflight-1.json'
class Refusal(RuntimeError):pass
def need(ok,message):
    if not ok:raise Refusal(message)
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def checked(record):
    p=Path(record['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical input')
    raw=p.read_bytes();need(len(raw)<=4*1024**2 and hashlib.sha256(raw).hexdigest()==record['sha256'],'input hash')
    return json.loads(raw)
def identity(p):
    s=Path(p).lstat();return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)))
def command(argv):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
    need(p.returncode==0 and p.stderr==b'' and len(p.stdout)<=4*1024**2,'bounded read-only command')
    return p.stdout.decode()
def static_joins(b):
    for record in b['source_pins']:
        need(hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()==record['sha256'],'frozen source')
    meta=checked(b['conditional_metadata']);proposal=checked(meta['proposal']);pending=checked(b['machine_pending'])
    need(meta['parent_identity']==proposal['parent']['identity']==b['parent_identity']==pending['parent_identity'],'parent static join')
    need(pending['independent_static_execution_decision']==b['static_review'],'static review join')
    checked(b['static_review'])
    need(proposal['profile']['mckernel_cpus']==2 and proposal['profile']['memory']==proposal['profile']['memory_swap']==12884901888,'fixed profile')
    spec=importlib.util.spec_from_file_location('two_cpu_snapshot_owner',N/'native_diagnostic_container_owner.py')
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    _,manifest=owner.bound_manifest(b['manifest']['path'],b['manifest']['sha256'])
    need(manifest['artifacts']['mckernel_image']['sha256']==b['repaired_image_sha256'] and manifest['pair']['host_cpus']==[1,2] and manifest['pair']['cpus']==[0,1],'fixed NEW205/two CPU authority')
    need(type(manifest.get('pair_rounds')) is int and manifest['pair_rounds']==2,'fixed two sequential pair rounds; no duration knob')
    return proposal,owner
def same_ref(a, b, label):
    need(a['path'] == b['path'] and a['sha256'] == b['sha256'], label)

def terminal_joins(t, b):
    need(t == checked(b['physical_review']), 'exact independent latest native physical report')
    need(t['schema'] == 'mckernel.independent-current-host-pair-finalrelease-physical-retirement.v1'
         and t['decision'] == 'PASS_CURRENT_FINALRELEASE_SINGLE_OWNER_POSITIVE_PHYSICAL_RETIREMENT_ONLY', 'native physical schema/decision; no invented status')
    need(t['physical_release'] is True and t['container_absent'] is True and t['owned_groups_empty'] is True and t['lease_retained'] is False, 'positive native physical retirement')
    c=b['physical_predecessor'];f=t['physical_facts']
    need(t['container_id']==c['container_id'] and t['owner_nonce']==c['owner_nonce'], 'latest native CID/owner nonce')
    need(f['operation_status']=='PROTOCOL_PASS' and f['absence_verified'] is True and f['container_absent'] is True and f['lease_retained'] is False and f['failure'] is None and f['secondary_errors']==[], 'actual native owner retirement')
    need(f['cleanup']=={'errors':[], 'reaped':True} and f['capture_errors']==[] and f['teardown'] is True and f['raw_capture_bindings_all_join'] is True, 'native child/capture retirement')
    s=f['container_state'];need(s['Status']=='exited' and s['Pid']==0 and s['ExitCode']==0 and s['OOMKilled'] is False and s['Running'] is False and s['Dead'] is False and s['Error']=='', 'retired native container')
    mutex=f['mutex'];need(mutex['present'] is True and (mutex['device'],mutex['inode'])==(b['root_lock_identity']['device'],b['root_lock_identity']['inode']), 'permanent mutex identity retained')
    # These are earlier released SDK record paths, not fictitious native leases.
    previous=checked(b['released_record_review']);request=checked(b['released_record_request'])
    need(previous['schema']=='mckernel.independent-current-parent-pin-sdk-physical-retirement.v1' and previous['status']=='PASS' and previous['physical_release'] is True and previous['current_owned_records_absent'] is True, 'retained released-record provenance')
    same_ref(previous['request'],b['released_record_request'],'released-record actual request')
    need(request['common_exclusion_path']==c['common_exclusion'] and request['lease_path']==c['lease_path'] and request['boot_id']==c['boot_id'], 'released-record exact paths/boot')
    need(not os.path.lexists(c['lease_path']), 'retained released SDK lease still absent')
def collect_live(b,proposal,owner):
    parent=Path(proposal['parent']['path']);scratch=Path(owner.SCRATCH);lock=Path(owner.LOCK)
    free=False
    with lock.open('r') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
        except BlockingIOError:pass
        finally:
            if free:fcntl.flock(stream,fcntl.LOCK_UN)
    names=['owner.stdout','owner.stderr','owner-join.json']+[f'readback-{i}.{suffix}' for i in range(1,4) for suffix in ('stdout','stderr','command.json')]
    paths=[b['physical_predecessor']['common_exclusion'],b['physical_predecessor']['shared_heavy']]
    capacity={}
    for path,floor in [(Path(owner.REPO),16*1024**3),(scratch,12*1024**3)]:
        s=os.statvfs(path);capacity[str(path)]={'available_bytes':s.f_bavail*s.f_frsize,'floor_bytes':floor,'reserve_bytes':402653184}
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    s=scratch.stat()
    return {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parent_identity':identity(parent),
      'parent_canonical':parent.resolve(strict=True)==parent,'parent_empty':not list(parent.iterdir()),
      'attempt_absent':not os.path.lexists(parent/('attempt-'+proposal['nonce'])),
      'owner_evidence_absent':not os.path.lexists(str(parent)+'.owner-'+proposal['nonce']),
      'fresh_outputs_absent':all(not os.path.lexists(N/name) for name in names) and not os.path.lexists(OUTPUT),
      'scratch_identity':[s.st_dev,s.st_ino],
      'mount':json.loads(command(['/usr/bin/findmnt','-J','-o','TARGET,UUID','-T',str(scratch)]))['filesystems'],
      'root_lock_identity':identity(lock),'root_mutex_snapshot_free':free,
      'released_paths_absent':{p:not os.path.lexists(p) for p in paths},
      'predecessor_container_absent':command(['/usr/bin/docker','ps','-aq','--no-trunc','--filter','id='+b['physical_predecessor']['container_id']])=='',
      'image_id':command(['/usr/bin/docker','image','inspect','--format','{{.Id}}',owner.IMAGE]).strip(),
      'image_record_sha256':hashlib.sha256(Path(owner.IMAGE_RECORD).read_bytes()).hexdigest(),
      'cgroup':{p:Path(p).read_text().strip() for p in owner.CGROUP},'capacity':capacity,
      'mem_available_bytes':int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])*1024,
      'launcher_phase':state['phase'],'launcher_stop_reason':state['stop_reason'],'included_usage_percent':state['last_rate_limits']['primary']['usedPercent']}
def validate_live(o,b,owner):
    need(o['boot_id']==b['physical_predecessor']['boot_id'],'current boot')
    need(o['parent_identity']==b['parent_identity'] and all(o[k] is True for k in ('parent_canonical','parent_empty','attempt_absent','owner_evidence_absent','fresh_outputs_absent')),'actual parent/fresh outputs')
    need(o['scratch_identity']==[1828,2] and o['mount']==[{'target':owner.SCRATCH,'uuid':b['physical_predecessor']['filesystem_uuid']}],'current scratch mount')
    need(o['root_lock_identity']==b['root_lock_identity'] and o['root_mutex_snapshot_free'] is True,'root mutex')
    need(o['released_paths_absent']=={b['physical_predecessor'][key]:True for key in ('common_exclusion','shared_heavy')} and o['predecessor_container_absent'] is True,'current physical/common/shared release')
    need(o['image_id']==owner.IMAGE and o['image_record_sha256']==owner.IMAGE_RECORD_SHA256 and o['cgroup']==owner.CGROUP,'actual image/cgroup')
    for path,floor in ((owner.REPO,16*1024**3),(owner.SCRATCH,12*1024**3)):
        row=o['capacity'][path];need(row['floor_bytes']==floor and row['reserve_bytes']==402653184 and row['available_bytes']>=floor+402653184,'capacity floors/reserve')
    need(o['mem_available_bytes']>=16*1024**3,'memory headroom')
    need(o['launcher_phase']=='running' and o['launcher_stop_reason'] is None and type(o['included_usage_percent']) in (int,float) and 0<=o['included_usage_percent']<97,'launcher/included usage')
def publish(result):
    with OUTPUT.open('x') as f:
        os.fchmod(f.fileno(),0o644)
        json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return ref(OUTPUT)
def main(argv=None):
    p=argparse.ArgumentParser(allow_abbrev=False)
    for flag in ('bindings-sha256','terminal','terminal-sha256'):p.add_argument('--'+flag,required=True)
    a=p.parse_args(argv);need(os.getuid()==os.geteuid()==0,'root read-only observer required')
    b=checked({'path':str(N/'fresh-snapshot-bindings.json'),'sha256':a.bindings_sha256})
    proposal,owner=static_joins(b);terminal_ref={'path':a.terminal,'sha256':a.terminal_sha256}
    terminal_joins(checked(terminal_ref),b)
    o=collect_live(b,proposal,owner);validate_live(o,b,owner)
    result=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=time.time(),parent_identity=b['parent_identity'],
      exclusive_heavy_accepted=True,root_mutex_snapshot_free=True,terminal_acceptance=terminal_ref,
      independent_static_execution_decision=b['static_review'],accepted_actual_stage_fixture_parent_review=b['static_review'],
      non_temporal_join_result=b['non_temporal_freeze'],boot_id=o['boot_id'],capacity=o['capacity'],
      mem_available_bytes=o['mem_available_bytes'],included_usage_percent=o['included_usage_percent'],
      heavy_profile={k:proposal['profile'][k] for k in ('cpuset','cpus','memory','memory_swap','pids','network')},
      guest_profile={'memory_mib':8192,'vcpus':4,'numa_nodes':2},released_paths_absent=list(o['released_paths_absent']),
      current_predecessor_container_absent=True,image_id=o['image_id'],cgroup=o['cgroup'])
    record=publish(result);print(json.dumps({'status':result['status'],**record}),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
