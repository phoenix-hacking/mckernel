"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only current executor context; reuses the accepted SDK stable-FD/tool readers.
No compiler, subprocess, owner entry, signal, grant, clock, or artifact write.
"""
import argparse,ast,hashlib,json,os,re,shlex,stat,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import validate_mcexec_default_batch as v

LEGACY=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-user-rustc-source-4/target_tools_sdk_driver.RETAINED-PREFIX-SUFFIX.SOURCE-ONLY.py')
LEGACY_SHA='30a86c386f09741a18e7873f0869526edb4bc3e63524bdfc47431ac8695de3a4'

def readers():
    raw=LEGACY.read_bytes();v.need(hashlib.sha256(raw).hexdigest()==LEGACY_SHA,'accepted stable-reader source changed')
    tree=ast.parse(raw);nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in ('need','digest','tool_digest'):nodes.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOOL_RULES' for t in node.targets):nodes.append(node)
    env=dict(Path=Path,os=os,stat=stat,hashlib=hashlib)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(LEGACY),'exec'),env)
    return env

def cache(path):
    result={}
    for line in path.read_text().splitlines():
        if line and not line.startswith(('#','//')) and '=' in line and ':' in line.split('=',1)[0]:
            key,value=line.split('=',1);result[key.split(':',1)[0]]=value
    return result

def command(makefile,needle):
    rows=[line.strip() for line in makefile.splitlines() if line.startswith('\t') and needle in line]
    v.need(len(rows)==1,'one exact generated command '+needle);return shlex.split(rows[0])
def buildid(raw):
    hits=re.findall(r'^#define BUILDID "([^"\n]+)"$',raw,flags=re.M)
    v.need(len(hits)==1,'one actual generated BUILDID');return hits[0]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--retained-context',type=Path,required=True);p.add_argument('--request',type=Path,required=True);p.add_argument('--compute-before',type=Path,required=True);a=p.parse_args()
    prep=json.loads(a.preparation.read_bytes());old=json.loads(a.retained_context.read_bytes());request=json.loads(a.request.read_bytes());before=json.loads(a.compute_before.read_bytes());r=readers();digest=r['digest']
    source=Path('/src');build=Path(v.BUILD);user=build/'executer/user';values=cache(build/'CMakeCache.txt')
    def hashed(path):return dict(bytes=path.stat().st_size,sha256=digest(path))
    tools={name:r['tool_digest'](name) for name in old['tool_hashes']}
    current={key:None for key in v.CONTEXT_FIELDS}
    current.update(runtime_sources={name:hashed(source/name) for name in old['runtime_sources']},rust_command=command((user/'CMakeFiles/mcexec_rust_helpers.dir/build.make').read_text(),'--crate-name mcexec_helpers'),rust_cwd=str(user),generated_BUILDID_rs=hashed(user/'rust/mcexec_buildid_generated.rs'),top_config_h=hashed(build/'config.h'),ihk_config_h=hashed(build/'ihk/config.h'),BUILDID=buildid((build/'config.h').read_text()),tool_hashes={name:row['sha256'] for name,row in tools.items()},image_id=request['image_id'],platform_ABI_prefix=old['platform_ABI_prefix'],ASM_source=hashed(source/'executer/user/arch/x86_64/archdep.S'),ASM_flags=(user/'CMakeFiles/libmcexec.dir/flags.make').read_text(),ASM_compile_command=command((user/'CMakeFiles/libmcexec.dir/build.make').read_text(),' -c /src/executer/user/arch/x86_64/archdep.S'),ASM_archive_command=(user/'CMakeFiles/libmcexec.dir/link.txt').read_text().splitlines())
    sdk=Path('/out').stat();current['selected_sdk_identity']=dict(old['selected_sdk_identity'],device=sdk.st_dev,inode=sdk.st_ino,uid=sdk.st_uid,gid=sdk.st_gid,mode=stat.S_IMODE(sdk.st_mode))
    v.need(values.get('BUILD_TARGET')=='smp-x86','selected x86_64 target')
    current['rust_cfg_profile']={k:(values.get(k,'OFF') in ('ON','TRUE','YES','1')) for k in old['rust_cfg_profile'] if k!='ARCH'};current['rust_cfg_profile']['ARCH']='x86_64'
    current['available_Rust_object']=hashed(Path(v.RUST_OBJECT)) if Path(v.RUST_OBJECT).exists() else None
    current['available_ASM_archive']=hashed(Path(v.ASM_ARCHIVE)) if Path(v.ASM_ARCHIVE).exists() else None
    # A link-only suffix never needs to force Make's timestamps. Missing ASM .o
    # or any unknown/missing generated prerequisite prevents Make reuse eligibility.
    obj=Path(v.RUST_OBJECT);asmobj=user/'CMakeFiles/libmcexec.dir/arch/x86_64/archdep.S.o'
    make=(user/'CMakeFiles/mcexec_rust_helpers.dir/build.make').read_text();prefix='executer/user/rust/mcexec_helpers.o: '
    deps=[line[len(prefix):] for line in make.splitlines() if line.startswith(prefix)]
    def path_for(logical):return Path(logical) if Path(logical).is_absolute() else build/logical
    asmmake=(user/'CMakeFiles/libmcexec.dir/build.make').read_text()
    asmprefix='executer/user/CMakeFiles/libmcexec.dir/arch/x86_64/archdep.S.o: '
    asmdeps=[line[len(asmprefix):] for line in asmmake.splitlines() if line.startswith(asmprefix)]
    arprefix='executer/user/libmcexec.a: '
    ardeps=[line[len(arprefix):] for line in asmmake.splitlines() if line.startswith(arprefix)]
    current['all_actual_Make_prerequisites_not_newer']=(bool(deps) and bool(asmdeps) and bool(ardeps) and obj.exists() and asmobj.exists() and Path(v.ASM_ARCHIVE).exists()
        and all(path_for(name).exists() and path_for(name).stat().st_mtime_ns<=obj.stat().st_mtime_ns for name in deps)
        and all(path_for(name).exists() and path_for(name).stat().st_mtime_ns<=asmobj.stat().st_mtime_ns for name in asmdeps)
        and all(path_for(name).exists() and path_for(name).stat().st_mtime_ns<=Path(v.ASM_ARCHIVE).stat().st_mtime_ns for name in ardeps))
    # Main batch always uses the current selected link command; it does not run Make.
    current['cache_values']=values;current['compute_RUSTC_before']=before['RUSTC'];current['compute_RUSTC_after']=values.get('RUSTC')
    current.update(source_CMake_sha256=digest(source/'executer/user/CMakeLists.txt'),IHK_user_CMake_sha256=digest(source/'ihk/linux/user/CMakeLists.txt'),selected_mcexec_source_list=[v.RUST_OBJECT],ASM_archive_only=True,generated_config_path=str(build/'config.h'),generated_IHK_config_path=str(build/'ihk/config.h'),generated_BUILDID_path=str(user/'rust/mcexec_buildid_generated.rs'),top_BUILDID=current['BUILDID'],IHK_BUILDID=buildid((build/'ihk/config.h').read_text()),Rust_BUILDID=None)
    rs=(user/'rust/mcexec_buildid_generated.rs').read_text();ids=re.findall(r'pub const BUILD_ID: &\[u8\] = b"([^"\n]+)\\0";',rs);v.need(len(ids)==1,'one actual Rust BUILDID data include');current['Rust_BUILDID']=ids[0]
    # Link/source selection is read from the actual generated rule, never asserted
    # merely from the planned CMake source or accepted object name.
    current['actual_generated_link_command']=shlex.split((user/'CMakeFiles/mcexec.dir/link.txt').read_text())
    link=current['actual_generated_link_command'];objects=[x for x in link if x.endswith('.o')]
    v.need(objects==['rust/mcexec_helpers.o'] and 'libmcexec.a' in link,'actual Rust-object/ASM-archive link selection')
    target=(user/'CMakeFiles/mcexec.dir/build.make').read_text();v.need('mcexec.c' not in target,'actual target includes C runtime')
    members=(user/'CMakeFiles/libmcexec.dir/link.txt').read_text();v.need('CMakeFiles/libmcexec.dir/arch/x86_64/archdep.S.o' in members and '.c.o' not in members,'actual ASM-only archive rule')
    v.validate_config(current);current['prefix_decision']=v.decide_prefix(old,current);current['tools_observed']=tools;current['schema']='mckernel.current-mcexec-producer-observation.v1';current['runtime_authority']=False
    print(json.dumps(current,sort_keys=True,indent=2))
if __name__=='__main__':main()
