"""Case-specific read-only root admission recipe; no owner or guest invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,time
N=Path(__file__).resolve().parent
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
    need(proposal['profile']['mckernel_cpus']==1 and proposal['profile']['memory']==proposal['profile']['memory_swap']==12884901888,'fixed inherited HOST66 profile')
    spec=importlib.util.spec_from_file_location('exact_m03_snapshot_owner',b['runtime_owner']['path'])
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    _,manifest=owner.bound_manifest(b['manifest']['path'],b['manifest']['sha256'])
    need(manifest['artifacts']['mckernel_image']['sha256']==b['repaired_image_sha256'],'actual accepted current NUMA image')
    need('pair' not in manifest and 'pair_rounds' not in manifest,'one M03 payload, no pair replay')
    need(manifest['payload']==b['payload_contract'],'complete unchanged NUMA payload/oracle')
    c=checked(b['mandatory_consumer_review']);s=checked(b['stage_review'])
    need(c['schema']=='mckernel.numa-native-app.actual-normalization-review.v1' and b['mandatory_consumer_review']['sha256']=='d7e94bbc4ceae6e5b04213e3beae0c221b2ee850150246ed9b6199a2b71063bb','actual current normalization acceptance')
    need(c['status']=='PASS_ACTUAL_NORMALIZATION_PARENT_AND_NO_EFFECT_ARGV_ONLY' and c['implementation_ownership'] is False and c['runtime_release'] is False,'normalization authority scope')
    need(s['schema']=='mckernel.numa-native-app.actual-offline-stage-review.v1' and s['decision']=='ACCEPT_EXACT_ACTUAL_MANIFEST_FOR_DOWNSTREAM_SOURCE_NORMALIZATION_AND_RUNTIME_PREPARATION','actual current stage ancestry')
    pre=checked(c['preflight']);binding=checked(c['binding'])
    need(set(c['normalized_manifest'])=={'path','sha256','size','mode'},'actual typed normalized manifest descriptor')
    accepted_manifest=dict(c['normalized_manifest'])
    need(binding['manifest']==accepted_manifest==b['manifest'],'complete accepted normalized manifest')
    need(c['parent_identity']==b['parent_review_identity']==pre['parent_nine_field_identity'] and pre['parent_identity']==b['parent_identity'],'complete actual parent roles')
    need(binding['nonce']==proposal['nonce']==pre['binding']['nonce'] and binding['attempt_parent']==proposal['parent']['path'],'actual fresh parent/nonce')
    need(owner.SOURCE_HASHES==b['runtime_source_hashes'] and pre['consumed_paths']==b['entire_consumed_paths'],'actual source map and consumed paths')
    need(pre['owner_argv']==b['accepted_owner_argv'] and pre['root_owner_argv']==b['root_owner_argv'] and pre['qemu_argv']==b['qemu_argv'] and pre['inside_owner_argv']==b['inside_argv'],'actual full root/inside/QEMU argv')
    need(proposal['argv']==pre['root_owner_argv'],'actual pinned host3.9 root caller')
    whole=checked(c['whole'])
    need(pre['guest_runs']==pre['root_operations']==pre['clocks_or_host_effects']==0 and set(whole)=={'returncode','direct_child_joined','process_group_absent','elapsed_seconds'} and whole['returncode']==0 and whole['direct_child_joined'] is True and whole['process_group_absent'] is True and type(whole['elapsed_seconds']) in (int,float) and whole['elapsed_seconds']>=0,'actual four-field closed no-effect normalization')
    facts=c['actual_capture_facts'];need(facts['returncode']==whole['returncode'] and facts['direct_child_joined'] is whole['direct_child_joined'] and facts['process_group_absent'] is whole['process_group_absent'] and facts['guest_runs']==0,'genuine normalization capture findings')
    for role in ('stdout','stderr'):
        row=c[role];need(set(row)=={'path','sha256','size','mode'},'actual typed normalization stream')
        path=Path(row['path']);raw=path.read_bytes();need(len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and path.stat().st_mode==row['mode'],'whole actual normalization stream bytes/mode')
        if role=='stderr':need(raw==b'','actual normalization empty stderr')
        else:
            output=json.loads(raw);need(output['status']==pre['status'] and output['guest_runs']==0 and output['QMP_bytes']==c['QMP_bytes']==pre['paths']['qmp_socket_bytes'] and output['consumed_paths']==c['consumed_path_count']==len(pre['consumed_paths']) and output['readonly_roots']==c['readonly_root_count']==len(pre['readonly_roots']),'actual normalization stdout/no-effect tuple')
    return proposal,owner
def same_ref(a, b, label):
    need(a == b, label)

def terminal_joins(t,b):
    source=Path(b['physical_projection_source']['path'])
    need(hashlib.sha256(source.read_bytes()).hexdigest()==b['physical_projection_source']['sha256'],'exact selected known-kind physical decoder')
    spec=importlib.util.spec_from_file_location('exact_host66_physical_projection',source)
    decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    need(decoder.project(t,b['physical_review'])==b['physical_predecessor'],'complete genuine HOST66 physical projection')
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
    b=checked({'path':str(N/'fresh-snapshot-bindings.json'),'sha256':a.bindings_sha256})
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
