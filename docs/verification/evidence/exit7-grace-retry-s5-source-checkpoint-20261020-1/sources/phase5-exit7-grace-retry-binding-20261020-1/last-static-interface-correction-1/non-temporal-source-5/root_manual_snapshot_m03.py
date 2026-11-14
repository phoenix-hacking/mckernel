"""Case-specific read-only root admission recipe; no owner or guest invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,time
N=Path('/home/holden/mckernel-work/host-preparation/phase5-exit7-grace-retry-binding-20261020-1/last-static-interface-correction-1/native-control-packet-5')
OUTPUT=N/'root-live-preflight-1.json'
class Refusal(RuntimeError):pass
def need(ok,message):
    if not ok:raise Refusal(message)
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'bytes':Path(path).stat().st_size}
def checked(record):
    p=Path(record['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical input')
    raw=p.read_bytes();need(len(raw)<=4*1024**2 and hashlib.sha256(raw).hexdigest()==record['sha256'],'input hash');need('bytes' not in record or len(raw)==record['bytes'],'whole descriptor bytes');need('size' not in record or (len(raw)==record['size'] and p.stat().st_mode==record['mode']),'whole typed descriptor size/mode')
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
    need(proposal['profile']['mckernel_cpus']==2 and proposal['profile']['memory']==proposal['profile']['memory_swap']==12884901888,'fixed inherited HOST66 profile')
    spec=importlib.util.spec_from_file_location('exact_m03_snapshot_owner',b['runtime_owner']['path'])
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    _,manifest=owner.bound_manifest(b['manifest']['path'],b['manifest']['sha256'])
    need(manifest['artifacts']['mckernel_image']['sha256']==b['repaired_image_sha256'],'fixed tested205 image')
    need('pair' not in manifest and 'pair_rounds' not in manifest,'one M03 payload, no pair replay')
    need(manifest['case_id']=='startup.nonzero-dualstream.rust.exit7','exact selected M03 case')
    need(manifest['payload']['argv']==['/bin/mcexec','-t','1','0','/apps/app'],'unchanged exact M03 app argv')
    need(manifest['payload']['oracle']==b['strict_oracle'],'whole73B oracle/exit/stderr unchanged')
    c=checked(b['mandatory_consumer_review']);s=checked(b['stage_review'])
    need(c['schema']=='mckernel.independent-actual-exit7-native-preparation-acceptance.v1' and c['decision']=='PASS_ACTUAL_EXIT7_BYTE_EXACT_NORMALIZATION_FRESH_PARENT_AND_FULL_OWNER_CREATE_INSIDE_QEMU_ARGV_ONLY','actual M03 parent and full argv acceptance')
    need(c['status']=='PASS' and c['actual_normalized_manifest_fresh_parent_and_full_argv_acceptance'] is True and c['actual_ordinary_preparation_acceptance'] is True and c['runtime_release'] is None and c['native_execution_authorized'] is False,'preparation only, no native substitution')
    need(s['schema']=='mckernel.independent-actual-exit7-init-only-offline-stage-acceptance.v1' and s['decision']=='PASS_ACTUAL_EXIT7_INIT_ONLY_RETIREMENT_GRACE_OFFLINE_STAGE' and s['status']=='PASS' and c['actual_stage_acceptance']==b['stage_review'],'actual exit7 init-only retirement-grace stage ancestry')
    pre=checked(c['actual_full_preflight']);binding=checked(c['actual_binding_result']);facts=c['facts']
    need(binding['manifest']==b['manifest'] and c['actual_normalized_manifest']['path']==b['manifest']['path'] and c['actual_normalized_manifest']['sha256']==b['manifest']['sha256'],'whole accepted normalized manifest roles')
    need(facts['parent_identity']==b['parent_identity']==pre['parent_identity'] and facts['parent_nine_field_identity']==b['parent_review_identity']==pre['parent_nine_field_identity'],'complete actual parent roles')
    need(binding['nonce']==proposal['nonce']==pre['binding']['nonce'] and binding['attempt_parent']==proposal['parent']['path'],'actual fresh parent and nonce')
    need(owner.SOURCE_HASHES==b['runtime_source_hashes'] and pre['consumed_paths']==b['entire_consumed_paths'],'whole actual current source map and paths')
    need(pre['owner_argv']==b['accepted_owner_argv'] and pre['qemu_argv']==b['qemu_argv'] and pre['inside_owner_argv']==b['inside_argv'],'actual full owner/runner/QEMU argv')
    need(proposal['argv']==b['root_owner_argv'],'exact sudo/pinned-python owner command')
    need(facts['guest_runs']==pre['guest_runs']==0 and facts['root_operations']==pre['root_operations']==0 and facts['clocks_or_host_effects']==pre['clocks_or_host_effects']==0,'actual current ordinary preparation has no guest/root/clock/backend effects')
    need(facts['actual_direct_wait0_group_absent_closedstreams'] is True and facts['observer_and_retirement_errors_null'] is True and facts['all_stream_full9identities_and_hashes_match'] is True and facts['stderr_bytes']==0,'actual current closed preparation facts')
    whole=checked(c['actual_whole']);joined=checked(c['actual_direct_join']);waited=checked(c['actual_direct_wait'])
    need(joined['returncode']==0 and joined['direct_child_joined'] is True and joined['group_absent'] is True and joined['error'] is None and joined['retirement_error'] is None and joined['timed_out'] is False and joined['remaining_group_members']==joined['unexpected_group_members']==[],'actual preparation positively joined and retired without observer errors')
    need(type(joined['pid']) is int and joined['pid']>0 and type(joined['start']) is int and joined['start']>0,'actual preparation child birth identity')
    need(waited==dict(pid=joined['pid'],start=joined['start'],returncode=0,direct_child_joined=True),'whole actual direct wait agrees with joined child identity/result')
    record=whole['record'];need(record==dict(joined,captures=record['captures'],closed_streams=True) and set(record['captures'])=={'stdout','stderr'},'whole actual record/direct join/closed two-stream capture equality')
    # Reuse the already pinned known-kind stable full-FD reader, including the
    # permission-string mode0o600 representation of these actual capture rows.
    reader_ref=b['physical_projection_source'];need(ref(reader_ref['path'])==reader_ref,'complete pinned current capture reader source')
    spec=importlib.util.spec_from_file_location('actual_preparation_full_FD_reader',reader_ref['path'])
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    for name in ('stdout','stderr'):
        stream=record['captures'][name];raw=reader.R.read_bytes(stream)
        need(c['actual_'+name]==dict(path=stream['path'],sha256=stream['sha256'],bytes=stream['size']) and len(raw)==stream['size'],'whole current accepted stream descriptor and full FD bytes '+name)
    need(record['captures']['stderr']['size']==facts['stderr_bytes']==0,'actual closed preparation stderr empty')
    return proposal,owner
def same_ref(a, b, label):
    need(a == b, label)

def terminal_joins(t,b):
    source=Path(b['physical_projection_source']['path'])
    need(hashlib.sha256(source.read_bytes()).hexdigest()==b['physical_projection_source']['sha256'],'exact selected known-kind physical decoder')
    spec=importlib.util.spec_from_file_location('exact_native_positive_physical_projection',source)
    decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    need(decoder.project(t,b['physical_review'])==b['physical_predecessor'],'complete genuine native-positive physical projection')
    need(t==checked(b['physical_review']),'whole selected terminal report retained without role projection')
    need(b['root_lock_identity']==dict(device=27,inode=4,uid=0,gid=0,mode='0o644'),'permanent root mutex identity; live check remains required')
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
        s=os.statvfs(path);capacity[str(path)]={'available_bytes':s.f_bavail*s.f_frsize,'floor_bytes':floor,'reserve_bytes':679477248}
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
    need(o['scratch_identity']==b['scratch_identity'] and o['mount']==[{'target':owner.SCRATCH,'uuid':b['physical_predecessor']['filesystem_uuid']}],'current scratch mount')
    need(o['root_lock_identity']==b['root_lock_identity'] and o['root_mutex_snapshot_free'] is True,'root mutex')
    need(o['released_paths_absent']=={b['physical_predecessor'][key]:True for key in ('common_exclusion','shared_heavy')} and o['predecessor_container_absent'] is True,'current physical/common/shared release')
    need(o['image_id']==owner.IMAGE and o['image_record_sha256']==owner.IMAGE_RECORD_SHA256 and o['cgroup']==owner.CGROUP,'actual image/cgroup')
    for path,floor in ((owner.REPO,16*1024**3),(owner.SCRATCH,12*1024**3)):
        row=o['capacity'][path];need(row['floor_bytes']==floor and row['reserve_bytes']==679477248 and row['available_bytes']>=floor+679477248,'capacity floors/reserve')
    need(o['mem_available_bytes']>=16*1024**3,'memory headroom')
    need(o['launcher_phase']=='running' and o['launcher_stop_reason'] is None and type(o['included_usage_percent']) in (int,float) and 0<=o['included_usage_percent']<100,'launcher/included usage')
def publish(result):
    with OUTPUT.open('x') as f:
        os.fchmod(f.fileno(),0o644)
        json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return ref(OUTPUT)
def main(argv=None):
    p=argparse.ArgumentParser(allow_abbrev=False)
    for flag in ('bindings-sha256','terminal','terminal-sha256'):p.add_argument('--'+flag,required=True)
    a=p.parse_args(argv);need(os.getuid()==os.geteuid()==0,'root read-only observer required')
    b=checked({'path':str(N/'ROOT-SNAPSHOT-BINDINGS.json'),'sha256':a.bindings_sha256})
    proposal,owner=static_joins(b);terminal_ref=b['physical_review'];need(terminal_ref['path']==a.terminal and terminal_ref['sha256']==a.terminal_sha256,'exact selected full terminal descriptor')
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
