"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse qualified six+four source bodies on accepted685; private source/data only.
"""
from pathlib import Path
import copy,difflib,hashlib,json,stat
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');BASE=E/'ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1';F3=E/'m14-f03-selected-residual-implementation-20261026-1/next-six-qualified-selector-integration-1';F6=E/'m14-f06-selected-residual-implementation-20261026-1/selected-context-range-backlog-1';HOST=F6.parent/'actual-context-range-host-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def checked(row):p=Path(row['path']);assert ref(p)==row;return p
f3path=F3/'SOURCE-HANDOFF.NOT-GRANTED.json';f6path=F6/'BACKLOG-RESULT.json';hostpath=HOST/'ACTUAL-BATCH-HANDOFF.json'
assert ref(f3path)['sha256']=='3b75f3f78c9274c9f715f60fee6b0847e6a95f62de32406777c4fd890544fc24';assert ref(f6path)['sha256']=='45cd9f0c00b0171f2279a0d3db7bba49f6a98f009ba90521c4918c7a07be2686';assert ref(hostpath)['sha256']=='5073ac7bee5763ec6cc173d7f6f3af0f47cfc374bff8d9d96b24ca9e5a5b2183'
f3=json.loads(f3path.read_text());f6=json.loads(f6path.read_text());host=json.loads(hostpath.read_text());assert host['all_returncodes_zero'] and host['all_direct_waited'] and host['all_groups_absent']
pre={};selected={};sources=[]
for row in f3['source_bindings']:
 rel=row['relative'];base=checked(row['preimage']);post=checked(row['postimage']);assert (R/rel).read_bytes()==base.read_bytes();pre[rel]=ref(R/rel);selected[rel]=post.read_text();sources.append(dict(owner='F03six',relative=rel,preimage=row['preimage'],postimage=row['postimage']))
arch='arch/x86_64/kernel/syscall.c';oldC=(R/arch).read_text();oldR=(R/'kernel/rust/syscall_policy.rs').read_text();a=oldC.splitlines(True);edits=[];cfgs=[];defs=[];newmodules={};suffixes=[]
for entry in f6['entries']:
 leaf=F6/entry['entry'];b=json.loads((leaf/'SOURCE-BINDINGS.json').read_text());spec=b['spec']
 for row in b['before']:
  if row['path'].endswith('/arch/x86_64/kernel/syscall.c'):assert row['sha256']==ref(R/arch)['sha256']
  if row['path'].endswith('/kernel/rust/syscall_policy.rs'):assert row['sha256']==ref(R/'kernel/rust/syscall_policy.rs')['sha256']
 for row in b['after']:checked(row)
 policy=(leaf/'syscall_policy.rs').read_text();assert policy.startswith(oldR);suffixes.append(policy[len(oldR):]);cfgs.append(spec['Rust']);defs.append(spec['C']);newmodules['kernel/rust/'+spec['leaf']]=checked(entry['module'])
 variant=(leaf/'syscall.c').read_text().splitlines(True)
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,variant,autojunk=False).get_opcodes():
  if tag!='equal':edits.append((i,j,variant[k:l],entry['entry']))
for left,right in zip(sorted(edits),sorted(edits)[1:]):assert left[1]<=right[0],('arch overlapping source edits',left[3],right[3])
merged=a[:]
for i,j,replacement,_ in sorted(edits,reverse=True):merged[i:j]=replacement
selected[arch]=''.join(merged);pre[arch]=ref(R/arch);selected['kernel/rust/syscall_policy.rs']+=''.join(suffixes)
cm=selected['kernel/CMakeLists.txt'];needle='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_mmap_dispatch_bridge_candidate")';assert cm.count(needle)==1;cm=cm.replace(needle,needle+''.join('\n\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+cfg+'")' for cfg in cfgs))
needle='\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_mmap_dispatch_bridge.rs")';assert cm.count(needle)==1;cm=cm.replace(needle,needle+''.join('\n\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/'+rel.removeprefix('kernel/')+'")' for rel in newmodules))
olddefs='MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS;MCKERNEL_RUST_F06_PRCTL_SET_REGISTER;MCKERNEL_RUST_F06_PRCTL_GET_REGISTER;MCKERNEL_RUST_F06_MMAP_DISPATCH_BRIDGE';assert cm.count('"'+olddefs+'"')==1;cm=cm.replace('"'+olddefs+'"','"'+olddefs+';'+';'.join(defs)+'"');selected['kernel/CMakeLists.txt']=cm
for rel,p in newmodules.items():assert not (R/rel).exists();selected[rel]=p.read_text()
for rel,text in selected.items():
 path=D/'candidate'/rel;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_text(text);path.chmod(0o400)
 before=(R/rel).read_text() if (R/rel).exists() else '';diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile=rel if before else '/dev/null',tofile=rel));(D/'patches').mkdir(mode=0o700,exist_ok=True);(D/'patches'/(rel.replace('/','__')+'.patch')).write_text(diff)
P=json.loads((BASE/'PROFILE.SOURCE-ONLY.json').read_text());oldexport=P['inputs']['source_directory_exports'][0];oldmanifest=json.loads(checked(oldexport['manifest']).read_text());snapshot=D/'rust-subtree';snapshot.mkdir(mode=0o700);files=[]
for old in oldmanifest['files']:
 original=checked(old['snapshot']);target=snapshot/old['relative'];target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(original.read_bytes());target.chmod(0o400);row=copy.deepcopy(old);row['predecessor_snapshot']=old['snapshot'];row['snapshot']=ref(target);files.append(row)
byrel={row['relative']:row for row in files};updates=['kernel/rust/syscall_policy.rs']+list(newmodules)
for rel in updates:
 short=rel.removeprefix('kernel/rust/');target=snapshot/short
 if target.exists():target.chmod(0o600)
 target.write_bytes((D/'candidate'/rel).read_bytes());target.chmod(0o400);old=byrel.get(short,{});byrel[short]=dict(old,relative=short,original=old.get('original'),snapshot=ref(target),kind='ten-selector qualified source successor',qualified_origin=ref(D/'candidate'/rel))
manifest=dict(oldmanifest,export_root=str(snapshot),files=[byrel[k] for k in sorted(byrel)],new_leaf_files=[Path(rel).name for rel in newmodules],predecessor_manifest=oldexport['manifest'],changed_predecessor_files=['syscall_policy.rs'],total_bytes=sum(row['snapshot']['bytes'] for row in byrel.values()),original_source_mutations=0);save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',manifest)
# Same reviewed four-command consumer and eight retained C prefix inputs.
P['status']='STATIC_TEN_QUALIFIED_SELECTORS_ON_ACCEPTED685_NO_REQUEST_CUSTODY_OR_EXECUTION_AUTHORITY';P['request_sha256']=None;P['native_custody_clearance']=None;P['inputs']['source_directory_exports']=[dict(oldexport,host_path=str(snapshot),manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
for row in P['inputs']['postimages']:
 rel=row['relative']
 if rel in selected:post=D/'candidate'/rel;row['postimage']=ref(post);row['postimage_mode']=stat.S_IMODE(post.stat().st_mode)
P['cohort_source_bindings']=[dict(relative=row['relative'],postimage=row['postimage']) for row in P['inputs']['postimages']]+[dict(relative='kernel/rust/'+row['relative'],postimage=row['snapshot']) for row in manifest['files']]
for index,additions in [(0,f3['new_Rust_cfgs']+cfgs),(1,f3['new_C_defines']),(2,defs)]:
 argv=P['exact_commands'][index]['argv'];position=next(i for i,arg in enumerate(argv) if arg.startswith('--emit=obj=')) if index==0 else next(i for i,arg in enumerate(argv) if arg.startswith('-I'))
 tokens=[t for cfg in additions for t in ['--cfg',cfg]] if index==0 else ['-D'+flag for flag in additions]
 assert all((cfg not in argv if index==0 else '-D'+cfg not in argv) for cfg in additions);argv[position:position]=tokens
producer=json.loads((BASE/'OUTPUT/work/evidence/producer-contract.json').read_text())
for row in P['inputs']['objects']:
 if row['replace']:
  path=BASE/'OUTPUT/work/output/build'/row['build_relative'];row['source']=ref(path);row['action']='new ten-selector object; accepted685 predecessor provenance';row['retained_archive_member']=str(path)
P['reuse_descriptor']=str(D/'FROZEN-TEN-SELECTOR-EIGHT-OBJECT-REUSE-INPUTS.json');P['producer_contract']['source']='Accepted685 source+ten qualified selectors; same eight C prefixes and closed105fileRust directory';P['producer_contract']['postbuild_required'] += ['Prepublished ten-selector actual symbol/import/source and warning acceptance inputs','Exact actual C removal sets and any source-supported compiler elision must be recorded, never inferred from planned count']
save('PROFILE.SOURCE-ONLY.json',P)
oldreuse=json.loads(Path(json.loads((BASE/'PROFILE.SOURCE-ONLY.json').read_text())['reuse_descriptor']).read_text());reuse=dict(oldreuse,schema='mckernel.ten-qualified-selector-four-command-eight-object-reuse.v1',objects=P['inputs']['objects'],postimages=P['inputs']['postimages'],source_directory_exports=P['inputs']['source_directory_exports'],runtime_authority=None,future_nonce=None,future_pid=None);reuse['commands']['exact_four_literal_argv']=P['exact_commands'];save('FROZEN-TEN-SELECTOR-EIGHT-OBJECT-REUSE-INPUTS.json',reuse)
export=json.loads((BASE/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json').read_text());export.update(author=None,decision=None,status='STATIC_TEN_SELECTOR_EXPORT_DRAFT_NOT_AUTHORITY',request_sha256=None,runtime_authority=None);export['qualified_readonly_files']=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[row['snapshot'] for row in manifest['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
plan=dict(scope=__doc__.splitlines()[0],status='PRIVATE_HOST_QUALIFIED_TEN_SELECTOR_SOURCE_DEFAULT_NOT_EXECUTED',runtime_authority=None,preimages=pre,postimages={rel:ref(D/'candidate'/rel) for rel in selected},qualified_F03=ref(f3path),qualified_F06_source=ref(f6path),qualified_F06_actual=ref(hostpath),prior_accepted_artifact=ref(E/'next-cohort-artifact-qualification-source-1/FINAL-ARTIFACT-QUALIFICATION.json'),prior_profile=ref(BASE/'PROFILE.SOURCE-ONLY.json'),all_twelve_prior_canonical_edits_preserved=True,arch_C_region_overlap_count=0,policy_merge='F03 exact callback promotions+refcount suffix, then four exact F06 module declarations appended; common f4ed policy preimage',new_C_defines=dict(kernel=f3['new_C_defines'],arch=defs),new_Rust_cfgs=f3['new_Rust_cfgs']+cfgs,new_Rust_algorithm_bodies=0,new_Rust_module_files=list(newmodules),Rust_snapshot_files=len(byrel),Rust_changed_existing_files=['syscall_policy.rs'],retained_C_inputs=8,commands=4,USE_NOCACHE_MMAP_defined=False,unsupported_ownership_or_config_holds_cleared=False,compiler_container_Git_canonical_actions=0,nonce=None,request_sha256=None,resource_authority=None,independent_execution_release=None)
save('COHERENT-TEN-SELECTOR-SOURCE-PLAN.NOT-GRANTED.json',plan)
print(json.dumps(dict(status=plan['status'],postimages=len(selected),snapshot_files=len(byrel),existing_Rust_files_changed=['syscall_policy.rs'],new_module_files=len(newmodules),commands=4,retained_C_inputs=8,arch_overlaps=0)))
