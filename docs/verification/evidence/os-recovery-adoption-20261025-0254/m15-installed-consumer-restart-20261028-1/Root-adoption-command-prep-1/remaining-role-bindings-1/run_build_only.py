"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One admitted build-only Docker operation under an externally held one-heavy reservation.
Default describes the profile; --execute requires new exact root/review/resource inputs.
"""
import argparse,hashlib,json,os,stat,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent
DEADLINE=1793253600
MEMORY=12884901888
BUDGET=23259332608  # current aggregate21.661941528320312GiB ceiling
PROTECTED_SUFFIX='actual-current290-default-image-attempt-5'
SUDO_DOCKER_PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']

def require(ok,message):
    if not ok:raise RuntimeError(message)
def reference(path):
    p=Path(path);h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest())
def auth(row):
    require(isinstance(row,dict) and set(row)=={'path','bytes','sha256'},'exact authenticated reference required')
    require(reference(row['path'])==row,'reference bytes changed');return Path(row['path'])
def read(path):return json.loads(Path(path).read_text())
def strict_parent(path):
    p=Path(path);require(p.is_absolute() and '..' not in p.parts,'absolute normalized path required')
    for parent in reversed([p.parent,*p.parent.parents]):
        require(not parent.is_symlink() and parent.is_dir(),'ordinary non-symlink ancestry')
    return p

def resource_guards(profile,grant,review,resources,now,memavailable,host_threads,thread_limit,lock_rows,holder_start):
    require(now<DEADLINE and 0<=now-resources['observed_at_epoch']<=120,'fresh resource admission within fixed window')
    require(grant['author']=='/root' and grant['decision']=='GRANT_ONE_BFD_CURRENT_DEFAULT_BUILD_ONLY' and grant['maximum_invocations']==1,'new one-use root build-only grant required')
    require(review['decision']=='PASS_EXACT_BUILD_ONLY_EXECUTION' and review['independent'] is True and review['reviewer'] not in ('/root/default_link_repair','/root'),'independent exact execution review required')
    require(resources['author']=='/root' and resources['runtime_authority']=='ONE_BUILD_ONLY_RESOURCE_RESERVATION','readonly descriptor is not resource authority')
    require(grant['nonce']==review['nonce']==resources['nonce'],'same one-use admission identity')
    require(resources['cpus']==[2,3,4,5] and resources['heavy_slots_held']==1 and resources['other_heavy_slots']==0,'actual four-CPU reservation and one-heavy admission required')
    require(resources['reservation_owner']==grant['nonce'] and resources['cpu_reservation_held'] is True,'live CPU reservation required')
    require(resources['container_memory_bytes']==MEMORY and resources['container_pids']==512,'unchanged reviewed container limits')
    other=resources['other_reserved_memory_bytes'];budget=resources['aggregate_memory_budget_bytes']
    require(type(other) is int and other>=0 and type(budget) is int and 0<budget<=BUDGET and other+MEMORY<=budget,'aggregate memory planning ceiling')
    require(memavailable>=other+MEMORY+(4<<30),'fresh MemAvailable covers all reservations and host reserve')
    require(type(resources['other_reserved_pids']) is int and resources['other_reserved_pids']>=0,'explicit aggregate PID reservation required')
    require(resources['other_reserved_pids']+512<=resources['aggregate_pid_budget']<=thread_limit,'aggregate PID planning ceiling')
    require(host_threads+512+resources['other_reserved_pids']<=thread_limit,'physical host thread headroom')
    holder=resources['reservation_holder']
    require(holder_start==holder['starttime'],'positive reservation holder PID/start identity')
    dev=holder['device'];ino=holder['inode'];pid=holder['pid']
    token='%02x:%02x:%d'%(os.major(dev),os.minor(dev),ino)
    require(any(len(v)>=8 and v[1]=='FLOCK' and v[2]=='ADVISORY' and v[3]=='WRITE' and v[4]==str(pid) and v[5]==token and v[6:8]==['0','EOF'] for v in (s.split() for s in lock_rows.splitlines())),'actual live full-EOF CPU/heavy resource reservation flock')
    require(resources['coexistence_decision']=='REVIEWED_POSTCLEANUP_ONE_HEAVY','actual postcleanup one-heavy admission required')
    require(review['coexistence_decision']==resources['coexistence_decision'],'matching independent coexistence decision')
    require(resources['native_custody_unchanged'] is True,'native/global custody must remain untouched')

def mounts(profile,export,output):
    require(export['source_adoption']==profile['actual_source_adoption'],'exact adopted consumer source')
    require(export['readable_source_export']==profile['inputs']['source_export_root'],'exact private adopted source path')
    verify_bfd_source_export(profile)
    rows=[dict(r) for r in read(D/'STATIC-ROLE.SOURCE-ONLY.json')['read_only_mount_roles']]
    rows += [dict(host=str(D/'build_only_worker.py'),target='/build-only-worker.py',readonly=True),dict(host=str(output/'plan.json'),target='/build-only-plan.json',readonly=True)]
    return rows


def docker_prefix(profile,grant=None,review=None):
    require(profile['docker_client_prefix']==SUDO_DOCKER_PREFIX,'exact existing sudo Docker-client prefix only')
    if grant is not None:
        require(grant['docker_client_prefix']==review['docker_client_prefix']==SUDO_DOCKER_PREFIX and grant['root_docker_client_only'] is True and review['root_docker_client_only'] is True,'explicit exact root Docker-client mediation grant and review')
    return list(SUDO_DOCKER_PREFIX)

def docker_argv(profile,name,mount_rows,output):
    argv=docker_prefix(profile)+['run','--name',name,'--cidfile',str(output/'container.cid'),'--user','1000:1000','--read-only','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpuset-cpus','2-5','--memory',str(MEMORY),'--memory-swap',str(MEMORY),'--pids-limit','512','--tmpfs','/tmp:rw,nosuid,nodev,size=1073741824,mode=1777','--workdir','/work']
    argv+=['--mount','type=bind,source='+str(output/'work')+',target=/work']
    for row in mount_rows:
        require(row['readonly'] is True,'all input mounts readonly')
        require(',' not in row['host'] and ',' not in row['target'],'literal bind paths')
        argv+=['--mount','type=bind,source='+row['host']+',target='+row['target']+',readonly']
    argv += ['--entrypoint','/usr/bin/python3',profile['inputs']['image'],'-I','-B','/build-only-worker.py','/build-only-plan.json']
    return argv

def verify_bfd_source_export(profile):
    # Existing callback name retained; this role consumes Root's adopted SDK11 source.
    role=read(auth(profile['static_role']))
    require(profile['static_role']==reference(D/'STATIC-ROLE.SOURCE-ONLY.json'),'exact finite consumer role')
    require(profile['actual_source_adoption']==role['source_adoption'],'exact f24 adopted source receipt')
    adoption=read(auth(role['source_adoption']));root=strict_parent(profile['inputs']['source_export_root'])
    require(str(root)==role['source_root']==adoption['private_root'] and root.is_dir(),'same actual private source')
    require(adoption['author']=='/root' and adoption['status']=='PRIVATE_SOURCE_ADOPTED_FROM_ACCEPTED_BANK_NOT_EXECUTION_RELEASE' and adoption['runtime_authority'] is None,'source adoption does not supply execution authority')
    require(adoption['copied_finite_members']==6999 and adoption['source_bank_modified'] is False and adoption['accepted_export_replayed'] is False and adoption['SDK_rebuilt'] is False,'reuse adopted bank without export/SDK replay')
    require(len(adoption['verified_selected_inputs'])==58,'same finite selected consumer inputs')
    for row in adoption['verified_selected_inputs']:
        relative=Path(row['relative']);require(not relative.is_absolute() and '..' not in relative.parts,'normalized selected consumer path')
        p=root/relative;require(str(p)==row['actual']['path'] and p.is_file() and not p.is_symlink(),'ordinary selected source file')
        auth(row['actual'])
    layout=adoption['private_layout_change'];auth(layout['authentic_gitfile'])
    require(layout['real_metadata_host_directory']=='/home/holden/mckernel/.git/modules/ihk' and layout['container_readonly_destination']=='/source/.git/modules/ihk','authentic readonly metadata mount role')
    require((root/'ihk/.git').read_bytes()==b'gitdir: ../.git/modules/ihk\n','authentic 28-byte Git pointer')
    target=root/'.git/modules/ihk';require(target.is_dir() and not target.is_symlink() and not any(target.iterdir()),'empty genuine metadata bind target')
    require(profile['inputs']['read_only_mount_roles']==role['read_only_mount_roles'],'exact source/helper/SDK/toolchain readonly mounts')
    for row in profile['inputs']['qualified_readonly_files']:auth(row)
    return adoption

def commands_for_plan(profile):
    role=read(D/'STATIC-ROLE.SOURCE-ONLY.json')
    require(profile['static_role']==reference(D/'STATIC-ROLE.SOURCE-ONLY.json'),'exact consumer static role')
    auth(role['phase_contract']);auth(role['source_ready']);auth(role['independent_source_review'])
    require(profile['runtime_authority'] is None and role['runtime_authority'] is None,'source data supplies no runtime authority')
    require(profile['exact_commands']==role['exact_commands'] and len(profile['exact_commands'])==1,'one exact serial consumer leaf only')
    command=profile['exact_commands'][0]
    require(command['cwd']=='/work' and command['new_output']=='/work/evidence/current-consumer-producer.json','exact consumer receipt and outer cwd')
    require(profile['producer_contract']==role['producer_contract'],'exact consumer behavior contract')
    require(profile['inputs']['image']==role['image']=='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5','same accepted SDK image')
    return profile['exact_commands']


def current_operation_guard():
    import importlib.util
    guard_path=D/'runtime_guard.py'
    spec=importlib.util.spec_from_file_location('bfd_newwindow_runtime_guard',guard_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.guard()

def execute(grant_path):
    current_operation_guard()
    require(os.getuid()==os.geteuid()==1000,'host runner remains UID1000; only exact reviewed Docker-client prefix is elevated')
    profile=read(D/'PROFILE.SOURCE-ONLY.json');grant=read(grant_path)
    require(profile['runtime_authority'] is None,'profile cannot grant runtime authority')
    commands=commands_for_plan(profile)
    require(grant['runner']==reference(__file__) and grant['profile']==reference(D/'PROFILE.SOURCE-ONLY.json') and grant['worker']==reference(D/'build_only_worker.py'),'exact runner/profile/worker grant')
    review=read(auth(grant['review']));resources=read(auth(grant['resource_authority']));export=read(auth(grant['input_export_authority']))
    require(review['runner']==grant['runner'] and review['profile']==grant['profile'] and review['worker']==grant['worker'] and review['resource_authority']==grant['resource_authority'] and review['input_export_authority']==grant['input_export_authority'],'exact reviewed closure')
    docker_prefix(profile,grant,review)
    require(grant['native_custody_clearance']==review['native_custody_clearance']==resources['native_custody_clearance']==profile['native_custody_clearance'],'same accepted actual postcleanup clearance')
    auth(profile['native_custody_clearance'])
    ready=read(auth(resources['reservation_ready_record']))
    require(ready['holder']==resources['reservation_holder'] and ready['nonce']==grant['nonce'] and ready['status']=='ACTUAL_ONE_HEAVY_27_4_HELD_NOT_BUILD_ADMISSION','actual wrapper holder receipt required')
    require(export['author']=='/root' and export['decision']=='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS' and export['request_sha256']==profile['request_sha256'],'real read-permission/export binding required')
    require(export['runtime_authority'] is None,'input export descriptor supplies no execution authority')
    require(export['container_tool_files']==profile['inputs']['container_tool_files'] and export['container_sha256_pins']==profile['inputs']['container_sha256_pins'],'exact accepted tool/library/header pins')
    require(len(export['container_tool_files'])>=4 and {'/usr/bin/cmake','/usr/bin/cc','/usr/bin/ld','/nightly/bin/rustc'}<=set(x['path'] for x in export['container_tool_files']),'qualified exact Rust/GCC/linker/tool files required')
    require(export['Rust_release']=='1.95.0-nightly' and export['GCC_major']==14,'same pinned compiler versions; no HOST ABI substitution')
    require(export['SDK11_recompiled'] is False,'no SDK11/full-producer replay')
    require(export['source_adoption']==profile['actual_source_adoption'],'same actual Root selective adoption')
    verify_bfd_source_export(profile)
    require(export['current_entry_bindings']==review['current_entry_bindings']==resources['current_entry_bindings']==profile['current_entry_bindings'],'same genuinely current Root entry binding');auth(profile['current_entry_bindings'])
    require(export['source_writer_quiescence']==review['source_writer_quiescence']==profile['source_writer_quiescence'],'same independently reviewed actual Root source-writer interval')
    quiescence=read(auth(profile['source_writer_quiescence']));require(quiescence['author']=='/root','Root actual source-writer attestation required')
    output=strict_parent(grant['fresh_output_root'])
    require(review['fresh_output_root']==str(output) and resources['fresh_output_root']==str(output),'same fresh disjoint output')
    require(PROTECTED_SUFFIX not in str(output) and not os.path.lexists(output),'fresh output distinct from attempt5')
    originals=[x['host'] for x in profile['inputs']['read_only_mount_roles']]
    for original in originals:
        p=Path(original).resolve();require(p!=output and p not in output.parents and output not in p.parents,'outputs disjoint from protected inputs')
    holder=resources['reservation_holder'];reservation=strict_parent(holder['path']);st=reservation.lstat()
    require(stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino)==(holder['device'],holder['inode']),'pinned ordinary reservation identity')
    require((st.st_dev,st.st_ino)==(27,4) and resources['reservation_kind']=='PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE','actual postcleanup one-heavy permanent mutex reservation')
    # The parent wrapper holds the verified free global mutex; this child never unlocks it.
    proc=Path('/proc')/str(holder['pid']);start=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
    mem={r.split(':')[0]:r.split(':')[1].strip().split()[0] for r in Path('/proc/meminfo').read_text().splitlines()}
    resource_guards(profile,grant,review,resources,time.time(),int(mem['MemAvailable'])*1024,int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]),int(Path('/proc/sys/kernel/threads-max').read_text()),Path('/proc/locks').read_text(),start)
    require(os.statvfs(output.parent).f_bavail*os.statvfs(output.parent).f_frsize>=max(16<<30,resources['host_required_free_bytes']),'fresh host/scratch export capacity guard')
    scratch=Path('/home/holden/mckernel-work/scratch');sv=os.statvfs(scratch)
    require(sv.f_bavail*sv.f_frsize>=max(12<<30,resources['scratch_required_free_bytes']),'fresh actual scratch reserve guard')
    verify_bfd_source_export(profile)
    require(export['qualified_readonly_files']==profile['inputs']['qualified_readonly_files'],'exact source/toolchain/helper closure')
    for row in profile['inputs']['qualified_readonly_files']:auth(row)
    require(os.access(export['readable_source_export'],os.R_OK|os.X_OK),'UID1000 readable/traversable closed source')
    output.mkdir(mode=0o700);(output/'work').mkdir(mode=0o700);(output/'work/evidence').mkdir(mode=0o700)
    (output/'plan.json').write_text(json.dumps(dict(runtime_authority=None,deadline_epoch=DEADLINE,commands=commands,tool_files=export['container_tool_files'],tool_sha256_pins=export['container_sha256_pins'],producer_contract=profile['producer_contract'],source_profile=reference(D/'PROFILE.SOURCE-ONLY.json')),indent=2)+'\n')
    rows=mounts(profile,export,output)
    require(len({r['target'] for r in rows})==len(rows),'no duplicate RO mount targets')
    for row in rows:require(os.access(row['host'],os.R_OK),'actual UID1000 input bind read access')
    name='m15-current-consumer-'+grant['nonce'];require(name.replace('-','').isalnum() and len(name)<=120,'bounded container identity')
    current_operation_guard()
    argv=docker_argv(profile,name,rows,output)
    (output/'claim.json').write_text(json.dumps(dict(grant=reference(grant_path),argv=argv,pid=os.getpid(),scope=profile['scope'],native_authority=False),indent=2)+'\n')
    # No --rm or automatic kill/cleanup: exact positive local terminal proof is retained.
    with (output/'container.stdout').open('xb') as stdout,(output/'container.stderr').open('xb') as stderr:
        result=subprocess.run(argv,stdout=stdout,stderr=stderr,check=False)
    if not (output/'container.cid').exists():raise RuntimeError('container identity uncertain: preserve claim; root reconciles without replay')
    cid=(output/'container.cid').read_text().strip();require(len(cid)==64 and all(x in '0123456789abcdef' for x in cid),'exact captured container ID')
    state=subprocess.run(docker_prefix(profile,grant,review)+['inspect','--format','{{json .State}}',cid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True)
    terminal=json.loads(state.stdout);require(terminal['Running'] is False and terminal['Pid']==0,'positive local terminal container proof required')
    (output/'terminal.json').write_text(json.dumps(dict(returncode=result.returncode,container=cid,state=terminal,default_native_retirement_acceptance=False),indent=2)+'\n')
    current_operation_guard()
    require(result.returncode==terminal['ExitCode']==0 and not terminal['OOMKilled'],'build failed; preserve first result and stop')
    print(json.dumps(dict(status='BUILD_ONLY_COMPLETE_PENDING_PRODUCER_AND_ELF_ACCEPTANCE',output=str(output),container=cid)))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',metavar='EXACT_NEW_ROOT_GRANT');args=parser.parse_args()
    if args.execute:execute(Path(args.execute))
    else:print(json.dumps(dict(status='SOURCE_ONLY_NOT_RELEASED',runtime_authority=None,profile=str(D/'PROFILE.SOURCE-ONLY.json'),next_command=['/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve()),'--execute','ACTUAL_NEW_BUILD_ONLY_ROOT_GRANT.json'])))
if __name__=='__main__':main()
