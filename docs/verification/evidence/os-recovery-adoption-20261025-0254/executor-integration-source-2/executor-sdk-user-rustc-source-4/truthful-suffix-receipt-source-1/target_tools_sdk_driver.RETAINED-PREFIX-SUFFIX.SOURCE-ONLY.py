"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Selected SDK source/default tool compiler operation using accepted h990 ownership.
No device/CLI execution, Rust library rebuild, root action, or native credit.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,sys,time
entered=time.monotonic()
CONFIG = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-user-rustc-source-4/preparation.SUFFIX-SOURCE-ONLY.json')
CONFIG_SHA = '8d603e4fc5d61c2c2931a77064c7bb5a2a08664094bbbd797963c3db153306c7'
TOOL_RULES = {'/nightly/bin/rustc': ('readonly-mounted-nightly', '70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'), '/usr/bin/cc': ('readonly-image', '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'), '/usr/include/bfd.h': ('readonly-image', 'de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432'), '/usr/lib64/libbfd.so': ('readonly-image', '6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3'), '/usr/bin/cmake': ('readonly-image', 'a2ec9c59d15b48b6abba45cfaa873df186e01a2e3ca99302ada1e51637f4cfd1'), '/usr/bin/nm': ('readonly-image', 'df99ae7b36cf9aa2da1e447026082ae5faddb7d7f12ebce911503c3022ed4bf1'), '/usr/bin/readelf': ('readonly-image', 'c5e0de5f419ed907fdc0b7b0a6087ff5c54a8c68db4da01097bdf84a296349b7'), '/usr/bin/ar': ('readonly-image', '5da84ec1ebfbb2c6e9e0bc8ad12ba09bcbef053d2ed7841aa9bf2bed4bb92f54')}
D = Path('/work/output/m15-executor-captures')
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

def main():
 need(CONFIG_SHA is not None,'root must bind genuine executor materialization and fetched source authority')
 need(digest(CONFIG)==CONFIG_SHA,'exact executor packet');p=json.loads(CONFIG.read_bytes())
 need(p['schema']=='mckernel.sdk-executor-preparation.v1' and p['source_identity'] is not None,'exact bound executor preparation')
 for row in p['closure']:
  need(Path(row['path']).stat().st_size==row['bytes'] and digest(row['path'])==row['sha256'],'exact reused executor source')
 materialized=p['materialized_source']['result']
 need(materialized['sha256'] is not None and digest(materialized['path'])==materialized['sha256'],'actual executor materialization')
 result=json.loads(Path(materialized['path']).read_bytes())
 need(result['status']=='PASS_FINITE_TARGET_SOURCE_MATERIALIZATION_ONLY' and result['source_root']==p['materialized_source']['root'],'actual source copy result')
 validate_libdwarf_vendor(p['libdwarf_vendor'],p['libdwarf_vendor']['container_root'])
 validate_canonical_source_snapshot(p)
 need(os.getuid()==os.getgid()==1000 and os.sched_getaffinity(0)=={2,3,4,5},'reviewed SDK UID/CPUs')
 need(p['target_tools']=={k:v[1] for k,v in TOOL_RULES.items()},'exact pinned SDK tool aliases')
 before={k:tool_digest(k) for k in TOOL_RULES}
 plan=json.loads(Path(p['commands']['path']).read_bytes())
 need(digest(p['commands']['path'])==p['commands']['sha256'] and len(plan['commands'])==9,'exact nine executor commands')
 need(all(plan['commands'][3]['argv'].count(flag)==1 for flag in ('-DRUSTC:FILEPATH=/nightly/bin/rustc','-DMCKERNEL_RUNTIME_TOOL_RUSTC:FILEPATH=/nightly/bin/rustc','-DIHK_USER_RUSTC:FILEPATH=/nightly/bin/rustc')),'exact independent compute/runtime/libihk compilers in executor configure')
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
 need(not D.exists() and not Path('/work/evidence').exists(),'fresh executor captures/evidence')
 Path('/work/output').mkdir(mode=0o700);D.mkdir(mode=0o700);Path('/work/evidence').mkdir(mode=0o700);os.chdir(D)
 for s in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(s,ns['stop'])
 rows,prefix_provenance=validate_retained_executor_prefix(plan);Path('/work/output/m15-executor-sdk-default-1').mkdir(mode=0o700);artifacts={};receipt=dict(schema='mckernel.sdk-executor-default-receipt.v1',status='FAIL',commands=rows,artifacts=artifacts,native=False,default_acceptance=False,CLI_executed=False,C_library_TU=False,source_identity=p['source_identity'],configuration_sha256=CONFIG_SHA)
 receipt.update(retained_prefix=prefix_provenance,planned_new_command_indices=[3,4,5,6,7,8]);budget();signal.setitimer(signal.ITIMER_REAL,90-(time.monotonic()-entered))
 try:
  for item in plan['commands'][3:]:
   budget();q=D/('%02d'%item['index']);q.mkdir(mode=0o700)
   cmd=dict(argv=item['argv'],purpose=item['purpose']);ns['write'](q/'command.json',cmd)
   remaining=90-(time.monotonic()-entered);need(remaining>0,'shared90 deadline before phase launch')
   result=ns['owned_capture'](cmd,q,remaining,limits)
   rows.append(dict(command=item,result=result));ns['write'](q/'RESULT.json',rows[-1]);budget()
   need(positive(result),'first executor SDK command failure STOP')
  root=Path('/work/output/m15-executor-sdk-default-1/build')
  link=(root/'executer/user/CMakeFiles/mcexec.dir/link.txt').read_text()
  need('rust/mcexec_helpers.o' in link and 'libmcexec.a' in link and 'mcexec.c.o' not in link and '/retained/' not in link,'actual Rust plus reviewed ASM default link')
  need((D/'06/stdout').read_text().split()==['archdep.S.o'],'exact reviewed ASM archive member')
  nm=(D/'05/stdout').read_text().splitlines();need(sum(line.split()[-1:]==['main'] and line.split()[-2:-1]==['T'] for line in nm)==1,'unique Rust main')
  header=(root/'config.h').read_text();match=re.search(r'^#define BUILDID "([^"\\]*)"$',header,re.M);need(match is not None,'actual configured BUILDID')
  buildid=match[1].encode()+b'\0'
  expected='// Generated from the same BUILDID as config.h; contains data only.\npub const BUILD_ID: &[u8] = b"'+match[1]+'\\0";\n'
  need((root/'executer/user/rust/mcexec_buildid_generated.rs').read_text()==expected,'same configure generated Rust BUILDID')
  binary=root/'executer/user/mcexec';need(buildid in binary.read_bytes(),'actual binary BUILDID bytes; allocation proof separate')
  for rel in ['CMakeCache.txt','config.h','executer/user/rust/mcexec_buildid_generated.rs','executer/user/rust/mcexec_helpers.o','executer/user/libmcexec.a','executer/user/mcexec','executer/user/CMakeFiles/mcexec.dir/link.txt']:
   path=root/rel;artifacts[str(path)]=ns['hashed'](path,32<<20)
  validate_canonical_source_snapshot(p);need({k:tool_digest(k) for k in TOOL_RULES}==before,'stable tool source identities')
  budget();receipt.update(status='PASS_SELECTED_SDK_EXECUTOR_PRODUCER_ONLY',Rust_main=True,ASM_only_archive=True,generated_BUILDID_equal=True,BUILDID_binary_bytes=True,allocation_proof=False,all349_provider_parity=False,all51_data_ABI=False)
 except BaseException as error:
  receipt.update(error=repr(error));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);ns['write'](Path('/work/evidence/receipt.json'),receipt)
 print(json.dumps(dict(status=receipt['status'],commands=len(rows),native=False)))
if __name__=='__main__':main()
