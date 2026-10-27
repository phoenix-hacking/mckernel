"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Selected SDK source/default tool compiler operation using accepted h990 ownership.
No device/CLI execution, Rust library rebuild, root action, or native credit.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,sys,time
sys.path.insert(0, '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-mcexec-default-f4d-root-adoption-1')
import mcexec_contract as mc
import validate_mcexec_default_batch as batch
entered=time.monotonic()
CONFIG = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-mcexec-default-f4d-root-adoption-1/PREPARATION.json')
CONFIG_SHA = None
TOOL_RULES = {'/nightly/bin/rustc': ('readonly-mounted-nightly', '70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'), '/usr/bin/cc': ('readonly-image', '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'), '/usr/include/bfd.h': ('readonly-image', 'de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432'), '/usr/lib64/libbfd.so': ('readonly-image', '6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3'), '/usr/bin/cmake': ('readonly-image', 'a2ec9c59d15b48b6abba45cfaa873df186e01a2e3ca99302ada1e51637f4cfd1'), '/usr/bin/nm': ('readonly-image', 'df99ae7b36cf9aa2da1e447026082ae5faddb7d7f12ebce911503c3022ed4bf1'), '/usr/bin/readelf': ('readonly-image', 'c5e0de5f419ed907fdc0b7b0a6087ff5c54a8c68db4da01097bdf84a296349b7'), '/usr/bin/ar': ('readonly-image', '5da84ec1ebfbb2c6e9e0bc8ad12ba09bcbef053d2ed7841aa9bf2bed4bb92f54')}
D = Path('/work/mcexec-default-captures')
def need(ok, why):
    if not ok: raise RuntimeError(why)

def digest(p):
    p=Path(p);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_nlink==1,'regular singlelink source')
        value=hashlib.sha256();size=0
        for block in iter(lambda:os.read(fd,65536),b''):
            size+=len(block);need(size<=32<<20,'bounded input hash');value.update(block)
        last=os.fstat(fd);path=p.lstat()
        fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(size==last.st_size and all(getattr(first,k)==getattr(last,k)==getattr(path,k) for k in fields),'stable input FD')
        return value.hexdigest()
    finally:os.close(fd)

def tool_digest(alias):
    target=None; first_metadata=None; final_metadata=None; path_metadata=None; fd=None
    try:
        need(alias in TOOL_RULES, 'fixed tool alias required')
        tool_class,expected=TOOL_RULES[alias]
        target=Path(alias).resolve(strict=True)
        fd=os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        first=os.fstat(fd)
        first_metadata={k:getattr(first,k) for k in fields}
        need(stat.S_ISREG(first.st_mode) and
             (first.st_nlink==1 if tool_class=='readonly-mounted-nightly' else first.st_nlink>=1),
             'fixed tool regular/link policy')
        value=hashlib.sha256();size=0
        for block in iter(lambda:os.read(fd,65536),b''):
            size+=len(block);need(size<=32<<20,'bounded tool hash');value.update(block)
        last=os.fstat(fd);path=target.lstat()
        final_metadata={k:getattr(last,k) for k in fields}
        path_metadata={k:getattr(path,k) for k in fields}
        need(size==last.st_size and first_metadata==final_metadata==path_metadata,
             'stable fixed tool FD/path metadata')
        need(Path(alias).resolve(strict=True)==target,'fixed tool alias retargeted')
        digest_value=value.hexdigest();need(digest_value==expected,'exact pinned tool hash')
        return dict(alias=alias,tool_class=tool_class,resolved_path=str(target),sha256=digest_value,
                    first_metadata=first_metadata,final_metadata=final_metadata,path_metadata=path_metadata)
    except Exception as exc:
        raise RuntimeError('fixed tool alias='+str(alias)+' target='+str(target)+
                           ' first='+repr(first_metadata)+' final='+repr(final_metadata)+
                           ' path='+repr(path_metadata)+': '+str(exc)) from exc
    finally:
        if fd is not None:os.close(fd)

def retained_archive_snapshot(path):
    path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        first=os.fstat(fd);last=os.fstat(fd);named=path.lstat()
        fields=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
        need(stat.S_ISREG(first.st_mode) and first.st_nlink==1 and
             all(getattr(first,k)==getattr(last,k)==getattr(named,k) for k in fields),'stable retained archive FD metadata')
        return dict(device=first.st_dev,inode=first.st_ino,mode=oct(stat.S_IMODE(first.st_mode)),
                    nlink=first.st_nlink,uid=first.st_uid,gid=first.st_gid,size=first.st_size,
                    mtime_ns=first.st_mtime_ns,ctime_ns=first.st_ctime_ns)
    finally:os.close(fd)

def positive(r):
 return r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
def validate_libdwarf_vendor(spec, root, host_identity=False):
    import hashlib, json, os, stat
    from pathlib import Path
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def read_stable(path, expected_sha, expected_mode=None):
        path=Path(path)
        require(path.is_absolute() and path.resolve()==path, 'literal resolved vendor input')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            a=os.fstat(fd)
            require(stat.S_ISREG(a.st_mode) and a.st_size<=32<<20, 'bounded regular vendor source')
            if expected_mode is not None:
                require(stat.S_IMODE(a.st_mode)==expected_mode, 'exact vendor source mode')
            h=hashlib.sha256(); count=0
            while True:
                block=os.read(fd,65536)
                if not block: break
                count+=len(block);h.update(block)
            z=os.fstat(fd);n=path.lstat()
            fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
            require(all(getattr(a,k)==getattr(z,k)==getattr(n,k) for k in fields), 'stable9 vendor source')
            require(count==z.st_size and h.hexdigest()==expected_sha, 'accepted vendor source bytes')
        finally:
            os.close(fd)
    root=Path(root)
    require(root.is_absolute() and root.resolve()==root and root.is_dir(), 'exact vendor root')
    if host_identity:
        s=root.stat(); actual=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))
        require(actual==spec['HOST_identity'], 'retained vendor root identity')
    authority=spec['authority'];read_stable(authority['path'],authority['sha256'])
    selected=json.loads(Path(authority['path']).read_bytes())['consumed_gitlinks'][spec['gitlink']]
    require(selected['commit']==spec['commit'] and selected['files']==spec['files'] and len(selected['files'])==412, 'full accepted gitlink authority')
    require(set(spec['configure_and_target_required_paths'])<=selected['files'].keys(), 'finite CMake vendor closure')
    for relative,row in sorted(selected['files'].items()):
        rel=Path(relative)
        require(not rel.is_absolute() and '..' not in rel.parts and row['mode'] in ('100644','100755'), 'fixed vendor path/mode')
        read_stable(root/rel,row['sha256'],int(row['mode'],8)&0o777)
    return dict(verified_vendor_files=412,configure_and_target_paths=len(spec['configure_and_target_required_paths']),commit=spec['commit'])

def validate_canonical_source_snapshot(packet):
 for relative,row in packet['canonical_source_inputs'].items():
  path=Path('/src')/relative
  need(path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],'canonical actual source snapshot '+relative)

def validate_new_source_producer():
 base=Path('/work/output/whole70-tool-default/ihk/linux/user/rust/whole70')
 row=json.loads((base/'producer-receipt.json').read_bytes())
 need(row['status']=='PASS_REAL_HEADERS_AND_ONE_RUST_STATICLIB_BUILD_ONLY' and row['C_runtime_TU'] is False and row['native'] is False,'real canonical producer build scope')
 need(len(row['commands'])==10 and all(x['returncode']==0 for x in row['commands']),'four real-header compiles/five metadata runs/one Rust compile')
 last=row['commands'][-1]['argv']
 need(last[0]=='/nightly/bin/rustc' and last[-1]=='/src/ihk/linux/user/rust/whole70/libihklib_whole70.rs' and not any('/retained/' in a for a in last),'canonical source Rust invocation, no external archive shortcut')
 for flag in ('staticlib','ihklib_host_std_runtime','ihklib_stat_abi_stat','panic=abort','codegen-units=1','relocation-model=pic','opt-level=2','native-static-libs'):
  need(flag in last,'same real producer flag '+flag)
 need(row['stat_cfg']=='ihklib_stat_abi_stat' and (base/'actual-stat-cfg.txt').read_bytes()==b'ihklib_stat_abi_stat\n','actual generated platform cfg')
 native=['-lgcc_s','-lutil','-lrt','-lpthread','-lm','-ldl','-lc']
 need(row['native_static_libs']==native and (base/'native-static-libs.rsp').read_text().splitlines()==native,'samecompile native flag order')
 for name in ('perf_pages_abi.rs','dump_abi.rs','diagnostic_origins.rs','create_diagnostic_origins.rs'):
  need((base/name).is_file() and b'pub const ' in (base/name).read_bytes(),'actual header metadata '+name)
 need(row['archive']==str(base/'libihklib_whole70.a'),'new produced archive path')
 link=(Path('/work/output/whole70-tool-default/ihk/linux/user/CMakeFiles/ihklib.dir/link.txt')).read_text()
 need('libihklib_whole70.a' in link and 'native-static-libs.rsp' in link and '/retained/' not in link,'actual default library source-produced link inputs')
 return dict(canonical_source_produced=True,producer_commands=10,metadata_outputs=5,native_static_libs=native,archive=str(base/'libihklib_whole70.a'))

def validate_retained_executor_prefix(plan):
    # Exact prior00..02 evidence is reused; no ABI compile or readelf process is replayed.
    manifest=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-user-rustc-source-4/ACTUAL03C-CONFIGURE-FAILURE-AND-BOUNDED-SOURCE-CORRECTION.json')
    need(digest(manifest)=='4fabb4b2712a27a12270ae7286ded588254daf1f30b8e43a9e2046c68fed697a','exact actual03c retained-prefix manifest')
    prior=json.loads(manifest.read_bytes());rows=[]
    for expected,prefix in zip(plan['commands'][:3],prior['prefix'][:3]):
        need(expected['index']==prefix['index']==len(rows),'exact retained prefix index')
        for ref in prefix['files'].values():
            path=Path(ref['path']);need(path.stat().st_size==ref['bytes'] and digest(path)==ref['sha256'],'exact retained prefix input')
        row=json.loads(Path(prefix['files']['RESULT.json']['path']).read_bytes())
        need(row['command']==expected and positive(row['result']),'actual retained prefix positive joins')
        rows.append(row)
    artifact=prior['ABI_object'];need(Path(artifact['path']).stat().st_size==artifact['bytes'] and digest(artifact['path'])==artifact['sha256'],'retained ABI object unchanged')
    need(len(rows)==3,'complete retained prefix00..02')
    return rows,dict(manifest=str(manifest),sha256=digest(manifest),original_candidate=prior['actual_candidate'],indices=[0,1,2],replayed=False,ABI_object=artifact)

def configuration_api(preparation):
 return mc.configuration_api(preparation)

def selected_source_postflight(preparation,context):
 for name,row in context['runtime_sources'].items():
  path=Path('/src')/name
  need(path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],'selected executor source postflight '+name)
 expected={'executer/user/CMakeLists.txt':'1208a097f57f5b9d3deee4d23fc55c7c598d8a88aab9002d4c65ae13a36cea57',
           'ihk/linux/user/CMakeLists.txt':'a21e1cfbb064a03458201bfbea520d2f04e87ea287f58451d65031e74d728369',
           'ihk/linux/user/rust/ihkmond.rs':'0c0b4b6d286e9f0fdbdacf1d32c3cd33ec96d4d2420550771a0dc732dd84d86e'}
 expected.update({name:row['sha256'] for name,row in preparation['build_producer_sources'].items()})
 expected.update({'executer/user/rust/'+name:row['sha256'] for name,row in preparation['qualification_only_inputs'].items()})
 for name,sha in expected.items():need(digest(Path('/src')/name)==sha,'selected configure/ABI source postflight '+name)
 validate_libdwarf_vendor(preparation['libdwarf_vendor'],preparation['libdwarf_vendor']['container_root'])

def preparation_inputs(preparation,request):
 need(digest('/driver.py')==request['driver']['sha256'],'actual executing driver source')
 for row in preparation['closure']:
  path=Path(row['path']);need(path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],'exact executor input/support/retained ABI evidence')

def copy_prefix(preparation):
 root=Path(batch.BUILD);root.mkdir(mode=0o700,parents=True)
 for row in preparation['retained_prefix_files']:
  relative=Path(row['relative']);need(not relative.is_absolute() and '..' not in relative.parts,'finite relative prefix input')
  source=Path('/retained-f4d')/relative;need(digest(source)==row['sha256'] and source.stat().st_size==row['bytes'],'exact retained prefix before copy')
  output=root/relative;output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  # Fresh output only; preserve bytes, never alter source or forge timestamps.
  with output.open('xb') as stream:stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
  need(digest(source)==row['sha256']==digest(output),'stable retained prefix copy')

def main():
 global CONFIG_SHA
 request=json.loads(Path('/request.json').read_bytes());CONFIG_SHA=request['preparation']['sha256']
 need(request['preparation']['path']==str(CONFIG) and digest(CONFIG)==CONFIG_SHA,'exact authenticated executor preparation')
 p=json.loads(CONFIG.read_bytes());configuration_api(p)
 preparation_inputs(p,request)
 need(os.getuid()==os.getgid()==1000 and os.sched_getaffinity(0)=={2,3,4,5},'reviewed SDK UID/CPUs')
 need(p['target_tools']=={k:v[1] for k,v in TOOL_RULES.items()},'exact pinned SDK tools')
 before={k:tool_digest(k) for k in TOOL_RULES}
 validate_libdwarf_vendor(p['libdwarf_vendor'],p['libdwarf_vendor']['container_root'])
 h=p['capture_helper'];need(digest(h['path'])==h['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','h990')
 names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(Path(h['path']).read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':h['path']};exec(compile(ast.Module(body=nodes,type_ignores=[]),h['path'],'exec'),ns)
 def budget():
  a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN)
  need(a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime<=60,'whole CPU acceptance60')
  need(time.monotonic()-entered<90,'whole active wall90')
  need(sum(q.stat().st_size for q in Path('/work').rglob('*') if q.is_file())<=512<<20,'existing aggregate512MiB')
 def limits():
  for k,v in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)):resource.setrlimit(k,(v,v))
  os.sched_setaffinity(0,{2,3,4,5})
 need(not D.exists() and not Path('/work/evidence').exists() and not Path('/work/output').exists(),'fresh executor output/captures')
 Path('/work/output').mkdir(mode=0o700);D.mkdir(mode=0o700);Path('/work/evidence').mkdir(mode=0o700)
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
 rows=[];receipt=dict(schema='mckernel.mcexec-default-target-link-install.v1',status='FAIL',scope=batch.SCOPE,nonce=request['nonce'],preparation_sha256=CONFIG_SHA,request=dict(path=request['request_path'],sha256=digest(Path('/request.json'))),commands=rows)
 receipt.update({k:False for k in ('native_acceptance','whole_M15','all349_provider_parity','all51_data_ABI','allocation_proof','application_main_executed')})
 budget();signal.setitimer(signal.ITIMER_REAL,90-(time.monotonic()-entered))
 try:
  copy_prefix(p);budget()
  cache=Path(batch.BUILD)/'CMakeCache.txt';found=re.findall(r'^RUSTC:[^=]+=([^\n]+)$',cache.read_text(),re.M);need(len(found)==1,'actual before RUSTC')
  batch.validate_preconfigure_compute(dict(RUSTC=found[0]));need(found[0]==p['runtime']['preserved_compute_RUSTC'],'Root preserved compute compiler binding')
  ns['write'](Path('/work/evidence/COMPUTE-RUSTC-BEFORE.json'),dict(RUSTC=found[0]))
  context=None;link=None
  for index,item in enumerate(p['commands']):
   budget();q=D/('%02d'%index);q.mkdir(mode=0o700)
   if item['label']=='current-link':
    need(context is not None and context['prefix_decision']['decision']=='REUSE_EXACT_F4D_OBJECT_AND_ASM_ARCHIVE','exact F4D context required; changed inputs require a separately bound current compile, no replay')
    need(item['argv']==context['actual_generated_link_command'],'current actual generated link command differs')
   cmd=dict(argv=item['argv'],purpose=item['purpose']);ns['write'](q/'command.json',cmd)
   cwd=Path(item['cwd']);need(cwd.is_absolute() and str(cwd).startswith('/work') and '..' not in cwd.parts and cwd.is_dir(),'literal writable work cwd')
   os.chdir(cwd);remaining=90-(time.monotonic()-entered);need(remaining>0,'shared90 deadline before phase')
   result=ns['owned_capture'](cmd,q,remaining,limits);os.chdir(D)
   rows.append(dict(label=item['label'],command=cmd,result=result));ns['write'](q/'RESULT.json',rows[-1]);budget();need(positive(result),'first executor phase failure STOP')
   if item['label']=='producer-context':
    context=json.loads((q/'stdout').read_bytes());receipt['actual_config']=mc.file_ref(q/'stdout');receipt['actual_producer_context']=receipt['actual_config'];receipt['prefix_decision']=context['prefix_decision']
    need(context['prefix_decision']['decision']=='REUSE_EXACT_F4D_OBJECT_AND_ASM_ARCHIVE','current context changed or absent: '+json.dumps(context['prefix_decision']))
   if item['label']=='current-ELF-imports':
    link=mc.elf_proof((q/'stdout').read_text(),Path(batch.EXECUTABLE),context['actual_generated_link_command']);batch.validate_link(link)
    ns['write'](Path('/work/evidence/CURRENT-LINK-PROOF.json'),link);receipt['actual_link_proof']=mc.file_ref(Path('/work/evidence/CURRENT-LINK-PROOF.json'));receipt['current_build_ELF']=mc.file_ref(Path(batch.EXECUTABLE))
   if item['label']=='installed-ELF':
    installed=Path(p['stage'])/'usr/local/bin/mcexec';proof=mc.elf_proof((q/'stdout').read_text(),installed,context['actual_generated_link_command']);batch.validate_link(proof)
    expected,_=mc.elf.installed_bytes(Path(batch.EXECUTABLE).read_bytes(),'/usr/local');need(installed.read_bytes()==expected,'only exact CMake install RPATH change')
    receipt['actual_installed_ELF']=mc.file_ref(installed)
    install=dict(selected_component='mcexec_runtime',installed_path=str(installed),current_build_ELF=receipt['current_build_ELF'],actual_installed_ELF=receipt['actual_installed_ELF'],only_actual_CMake_install_changes=True)
    ns['write'](Path('/work/evidence/CURRENT-INSTALL-PROOF.json'),install);receipt['actual_install_proof']=mc.file_ref(Path('/work/evidence/CURRENT-INSTALL-PROOF.json'))
  selected_source_postflight(p,context)
  preparation_inputs(p,request)
  need({k:tool_digest(k) for k in TOOL_RULES}==before,'stable pinned SDK tools')
  batch.validate_batch_receipt(receipt|dict(status='PASS_MCEXEC_DEFAULT_TARGET_LINK_INSTALL_ONLY'),dict(nonce=request['nonce'],reference=receipt['request']),dict(sha256=CONFIG_SHA,retained_context=mc.file_ref(mc.HERE/'RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json'),stage=p['stage']))
  budget();receipt['status']='PASS_MCEXEC_DEFAULT_TARGET_LINK_INSTALL_ONLY'
 except BaseException as error:
  receipt['error']=repr(error);raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);ns['write'](Path('/work/evidence/receipt.json'),receipt)
 print(json.dumps(dict(status=receipt['status'],commands=len(rows),native=False)))

if __name__=='__main__':main()
