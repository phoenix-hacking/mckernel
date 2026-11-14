"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only exact next profile and narrow existing-runner source-directory adapter.
"""
from pathlib import Path
import copy,difflib,hashlib,json,stat
D=Path(__file__).resolve().parent;E=D.parent;F=E/'qualified-cohort-default-profile-source-1';BASE=E/'current290-unprivileged-build-only-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(name,v):(D/name).write_text(json.dumps(v,indent=2)+'\n')
plan=json.loads((D/'COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json').read_text());snapshot=json.loads((D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json').read_text());p=json.loads((F/'PROFILE.SOURCE-ONLY.json').read_text());p['status']='PRIVATE_EXACT_NEXT_COHORT_FIVE_COMMAND_PLAN_NO_REQUEST_OR_ADMISSION';p['runtime_authority']=None;p['request_sha256']=None
sources=[]
for rel in ['kernel/CMakeLists.txt','kernel/process.c','kernel/syscall.c','arch/x86_64/kernel/syscall.c']:
 base=Path(p['inputs']['source6153'])/rel;post=D/'candidate'/rel;sources.append(dict(relative=rel,base=ref(base),base_mode=stat.S_IMODE(base.stat().st_mode),postimage=ref(post),postimage_mode=stat.S_IMODE(post.stat().st_mode),container_destination='/src/'+rel,readonly=True))
p['inputs']['postimages']=sources;p['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
p['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in sources]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in snapshot['files']]
cmds=json.loads((F/'LITERAL-COMMAND-BASELINES.NOT-NEW-COHORT.json').read_text())['commands'];sel=plan['selection'];argv=cmds[0]['argv'];i=next(i for i,a in enumerate(argv) if a.startswith('--emit=obj='));argv[i:i]=[t for cfg in sel['Rust_cfg_additions'] for t in ['--cfg',cfg]]
for index,field in [(2,'kernel_syscall_C_defines'),(3,'arch_syscall_C_defines')]:
 argv=cmds[index]['argv'];i=next(i for i,a in enumerate(argv) if a.startswith('-I'));argv[i:i]=['-D'+flag for flag in sel[field]]
p['exact_commands']=cmds;p['reuse_descriptor']=str(D/'FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json');p['producer_contract']['source']='source6153 + exact four existing-target file postimages + closed kernel/rust directory successor';p['producer_contract']['process_delta']='UNCHANGED already qualified F02 process.c9692036c and exact GCC argv; existing process b8168c1f reuse candidate must be dispositioned before grant';p['producer_contract']['postbuild_required'] += ['qualified F03/F06 providers: actual full Rust plus selected syscall C objects, provider uniqueness, ABI and final link scope','closed kernel/rust directory source map and genuine NOCACHE-undefined context revalidation']
p['unchanged_completed_process_prefix']=dict(actual_F02_output=dict(path=str(E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o'),bytes=73408,sha256='b8168c1f52369f7909bf174fe1c926a4a4a3be4a63cd0667741841680b0ca289'),source_sha256='9692036c3aa2d580a2a134c2d4a8fc32ab5ff4215b44128668858d6fac131b12',argv_unchanged=True,Root_decision=None,execution_grant_allowed_before_disposition=False)
p['native_custody_clearance']=None # Root chooses actual current postjoin release after running guest joins.
save('PROFILE.SOURCE-ONLY.json',p)
reuse=json.loads(Path(json.loads((BASE/'PROFILE.SOURCE-ONLY.json').read_text())['reuse_descriptor']).read_text());reuse.update(schema='mckernel.current290.next-qualified-cohort-source-directory-seven-object-reuse.v1',runtime_authority=None,future_nonce=None,future_pid=None,postimages=sources,objects=p['inputs']['objects'],source_directory_exports=p['inputs']['source_directory_exports']);reuse['commands']['exact_five_literal_argv']=cmds;reuse['commands']['Rust_input_view']='Exact closed Rust directory successor; original F02 Rust cfg/flags retained plus only individually HOST-qualified new selectors';reuse['commands']['new_objects']=p['producer_contract']['new_objects'];reuse['commands']['status']='STATIC_PLAN_ROOT_MUST_DISPOSITION_UNCHANGED_PROCESS_PREFIX';save('FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json',reuse)
edits=json.loads((F/'run_build_only.py.edits.json').read_text())
helper='''def source_directory_postimages(profile):
    exports=profile['inputs'].get('source_directory_exports',[])
    require(isinstance(exports,list) and len(exports)<=1,'only one exact Rust subtree directory export')
    rows=[]
    for export in exports:
        require(set(export)=={'host_path','container_destination','readonly','manifest'} and export['readonly'] is True and export['container_destination']=='/src/kernel/rust','exact readonly Rust subtree source export')
        root=strict_parent(export['host_path']);require(root.is_dir() and not root.is_symlink(),'ordinary closed source directory')
        manifest=read(auth(export['manifest']))
        require(manifest['schema']=='mckernel.exact-kernel-rust-subtree-readonly.v1' and manifest['runtime_authority'] is None and manifest['export_root']==str(root) and manifest['container_destination']=='/src/kernel/rust' and manifest['base_source_root']==profile['inputs']['source6153']+'/kernel/rust','exact source-directory manifest binding')
        expected=set()
        for row in manifest['files']:
            relative=Path(row['relative']);require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==row['relative'],'exact normalized source-relative file')
            require(row['relative'] not in expected and row['snapshot']['path']==str(root/relative),'unique literal source snapshot file map')
            expected.add(row['relative']);rows.append(dict(relative='kernel/rust/'+row['relative'],postimage=row['snapshot']))
        actual=set()
        for path in root.rglob('*'):
            require(not path.is_symlink(),'no source-subtree symlinks')
            if path.is_dir():continue
            require(path.is_file(),'ordinary closed source snapshot file');actual.add(str(path.relative_to(root)))
        require(actual==expected,'closed exact source-directory file set')
    return rows

'''
text=edits['edits'][0]['after'];text=helper+text
text=text.replace("profile['cohort_source_bindings']==[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]","profile['cohort_source_bindings']==[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]+source_directory_postimages(profile)")
text=text.replace("{r['relative'] for r in profile['inputs']['postimages']}","{r['relative'] for r in profile['inputs']['postimages']}|{r['relative'] for r in source_directory_postimages(profile)}")
# A source-only profile cannot bypass the completed-prefix disposition.
needle="    commands=profile['exact_commands']"
text=text.replace(needle,"    if 'unchanged_completed_process_prefix' in profile:require(profile['unchanged_completed_process_prefix']['Root_decision'] is not None,'Root must disposition already completed unchanged F02 process prefix before grant')\n"+needle)
edits['edits'][0]['after']=text
needle="    base += [dict(host=r['host_path'],target=r['container_path'],readonly=True) for r in profile['inputs']['toolchain_mounts']]"
edits['edits'].append(dict(before=needle,after=needle+"\n    source_directory_postimages(profile)\n    base += [dict(host=r['host_path'],target=r['container_destination'],readonly=True) for r in profile['inputs'].get('source_directory_exports',[])]"))
needle="    for original in originals:"
edits['edits'].append(dict(before=needle,after="    originals += [r['host_path'] for r in profile['inputs'].get('source_directory_exports',[])]\n"+needle))
needle="+[r['postimage'] for r in profile['inputs']['postimages']]"
edits['edits'].append(dict(before=needle,after=needle+"+[r['postimage'] for r in source_directory_postimages(profile)]"))
save('run_build_only.py.edits.json',edits)
s=Path(edits['baseline']['path']).read_text();new=s
for edit in edits['edits']:
 assert new.count(edit['before'])==1,(edit['before'][:80],new.count(edit['before']));new=new.replace(edit['before'],edit['after'])
(D/'run_build_only.py.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile='run_build_only.py',tofile='run_build_only.py')))
for name in ['build_only_worker.py.edits.json','build_only_worker.py.patch']:(D/name).write_bytes((F/name).read_bytes())
# Corrected existing IHK/config exports are retained; directory snapshot is an
# explicit project-source export, never masquerading as a toolchain mount.
export=json.loads((E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json').read_text());export.update(author=None,decision=None,status='STATIC_NEXT_COHORT_EXPORT_DRAFT_NOT_AUTHORITY',runtime_authority=None,request_sha256=None);export['qualified_readonly_files']=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in sources]+[r['snapshot'] for r in snapshot['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
save('REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json',dict(scope=p['scope'],runtime_authority=None,nonce=None,request_sha256=None,grant=None,exact_commands=cmds,source_plan=ref(D/'COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json'),reuse=ref(D/'FROZEN-EXACT-NEXT-COHORT-REUSE-INPUTS.json'),Rust_directory_manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),process_prefix_disposition_required=p['unchanged_completed_process_prefix']))
print(json.dumps(dict(status='NEXT_PROFILE_AND_NARROW_SOURCE_DIRECTORY_PATCH_WRITTEN',source_directory_files=len(snapshot['files']),literal_commands=len(cmds),request_and_current_custody_and_process_disposition_null=True)))
