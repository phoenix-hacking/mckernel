"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One admitted build-only Docker operation under an externally held one-heavy reservation.
Default describes the profile; --execute requires new exact root/review/resource inputs.
"""
import argparse,hashlib,json,os,stat,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent
DEADLINE=1793100290
MEMORY=12884901888
BUDGET=23669457394  # no larger than 22.0439 GiB; confirmed in pure tests
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
    require(grant['author']=='/root' and grant['decision']=='GRANT_ONE_CURRENT290_BUILD_ONLY' and grant['maximum_invocations']==1,'new one-use root build-only grant required')
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
    require(export['source6153']==profile['inputs']['source6153'],'exact immutable source origin')
    require(export['retained_seed']==profile['inputs']['retained_seed'],'exact retained seed origin')
    base=[dict(host=export['readable_source_export'],target='/src',readonly=True),dict(host=export['readable_seed_export'],target='/seed-build',readonly=True)]
    base += [dict(host=r['host_path'],target=r['container_path'],readonly=True) for r in profile['inputs']['toolchain_mounts']]
    base += [dict(host=r['postimage']['path'],target=r['container_destination'],readonly=True) for r in profile['inputs']['postimages']]
    # Exports cover generated includes/SDK aliases/gitlinks needed by this exact command.
    # The entire literal set is bound to independent review; never infer permission.
    for row in export['additional_readonly_exports']:
        require(set(row)=={'host','target','readonly'} and row['readonly'] is True,'only exact readonly additional exports')
        require(row['target'] in ('/src/ihk','/work/output/build/kernel/include') or row['target'].startswith(('/src/ihk/','/out/','/work/output/build/kernel/include/')),'bounded immutable generated/SDK/gitlink aliases')
        base.append(row)
    for row in profile['inputs']['configuration']:
        base.append(dict(host=row['source']['path'],target='/work/output/build/'+row['build_relative'],readonly=True))
    for row in profile['inputs']['objects']:
        if not row['replace']:base.append(dict(host=row['source']['path'],target='/work/output/build/'+row['build_relative'],readonly=True))
    base.append(dict(host=profile['reuse_descriptor'],target='/reuse-inputs.json',readonly=True))
    base += [dict(host=str(D/'build_only_worker.py'),target='/build-only-worker.py',readonly=True),dict(host=str(output/'plan.json'),target='/build-only-plan.json',readonly=True)]
    return base

def docker_prefix(profile,grant=None,review=None):
    require(profile['docker_client_prefix']==SUDO_DOCKER_PREFIX,'exact existing sudo Docker-client prefix only')
    if grant is not None:
        require(grant['docker_client_prefix']==review['docker_client_prefix']==SUDO_DOCKER_PREFIX and grant['root_docker_client_only'] is True and review['root_docker_client_only'] is True,'explicit exact root Docker-client mediation grant and review')
    return list(SUDO_DOCKER_PREFIX)

def docker_argv(profile,name,mount_rows,output):
    argv=docker_prefix(profile)+['run','--name',name,'--cidfile',str(output/'container.cid'),'--user','1000:1000','--read-only','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpuset-cpus','2-5','--memory',str(MEMORY),'--memory-swap',str(MEMORY),'--pids-limit','512','--tmpfs','/tmp:rw,nosuid,nodev,size=1073741824,mode=1777','--workdir','/work/output/build/kernel']
    argv+=['--mount','type=bind,source='+str(output/'work')+',target=/work']
    for row in mount_rows:
        require(row['readonly'] is True,'all input mounts readonly')
        require(',' not in row['host'] and ',' not in row['target'],'literal bind paths')
        argv+=['--mount','type=bind,source='+row['host']+',target='+row['target']+',readonly']
    argv += ['--entrypoint','/usr/bin/python3',profile['inputs']['image'],'-I','-B','/build-only-worker.py','/build-only-plan.json']
    return argv

def execute(grant_path):
    require(os.getuid()==os.geteuid()==1000,'host runner remains UID1000; only exact reviewed Docker-client prefix is elevated')
    profile=read(D/'PROFILE.SOURCE-ONLY.json');grant=read(grant_path)
    require(profile['runtime_authority'] is None,'profile cannot grant runtime authority')
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
    require(len(export['container_tool_files'])>=4 and {'/usr/bin/cmake','/usr/bin/cc','/usr/bin/ld','/nightly/bin/rustc'}<=set(x['path'] for x in export['container_tool_files']),'qualified exact Rust/GCC/linker/tool files required')
    require(export['Rust_release']=='1.95.0-nightly' and export['GCC_major']==14,'same pinned compiler versions; no HOST ABI substitution')
    require(read(profile['reuse_descriptor']).get('runtime_authority') is None,'readonly descriptor supplies no runtime authority')
    require(export['SDK21_recompiled'] is False and export['source6153_entries']==6153,'preserve exact source and SDK reuse scope')
    output=strict_parent(grant['fresh_output_root'])
    require(review['fresh_output_root']==str(output) and resources['fresh_output_root']==str(output),'same fresh disjoint output')
    require(PROTECTED_SUFFIX not in str(output) and not os.path.lexists(output),'fresh output distinct from attempt5')
    originals=[profile['inputs']['source6153'],profile['inputs']['retained_seed']]+[x['host_path'] for x in profile['inputs']['toolchain_mounts']]+[export['readable_source_export'],export['readable_seed_export']]
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
    # Check only qualified file identities, not broad source inventories.
    expected=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in profile['inputs']['postimages']]
    require(export['qualified_readonly_files']==expected,'exact retained configuration/nine objects/three postimage export closure')
    for row in expected:auth(row)
    require(all(os.access(x,os.R_OK|os.X_OK) for x in (export['readable_source_export'],export['readable_seed_export'])),'actual UID1000 readable/traversable root exports')
    output.mkdir(mode=0o700);(output/'work').mkdir(mode=0o700)
    (output/'work/evidence').mkdir(mode=0o700);(output/'work/output').mkdir(mode=0o700)
    build=output/'work/output/build';(build/'kernel/rust').mkdir(mode=0o700,parents=True)
    for row in profile['inputs']['configuration']+[r for r in profile['inputs']['objects'] if not r['replace']]:
        target=build/row['build_relative'];target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.touch(mode=0o400,exist_ok=False)
    commands=[dict(c,new_output='/work/output/build/kernel/'+token) for c,token in zip(profile['exact_commands'],['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img'])]
    (output/'plan.json').write_text(json.dumps(dict(runtime_authority=None,deadline_epoch=DEADLINE,commands=commands,tool_files=export['container_tool_files'],producer_contract=profile['producer_contract'],source_profile=reference(D/'PROFILE.SOURCE-ONLY.json')),indent=2)+'\n')
    rows=mounts(profile,export,output)
    require(len({r['target'] for r in rows})==len(rows),'no duplicate RO mount targets')
    for row in rows:require(os.access(row['host'],os.R_OK),'actual UID1000 input bind read access')
    name='current290-build-only-'+grant['nonce'];require(name.replace('-','').isalnum() and len(name)<=120,'bounded container identity')
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
    require(result.returncode==terminal['ExitCode']==0 and not terminal['OOMKilled'],'build failed; preserve first result and stop')
    print(json.dumps(dict(status='BUILD_ONLY_COMPLETE_PENDING_PRODUCER_AND_ELF_ACCEPTANCE',output=str(output),container=cid)))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',metavar='EXACT_NEW_ROOT_GRANT');args=parser.parse_args()
    if args.execute:execute(Path(args.execute))
    else:print(json.dumps(dict(status='SOURCE_ONLY_NOT_RELEASED',runtime_authority=None,profile=str(D/'PROFILE.SOURCE-ONLY.json'),next_command=['/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve()),'--execute','ACTUAL_NEW_BUILD_ONLY_ROOT_GRANT.json'])))
if __name__=='__main__':main()
