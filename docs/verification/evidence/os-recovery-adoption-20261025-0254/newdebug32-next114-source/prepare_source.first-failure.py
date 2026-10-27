"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Selective existing debug32 composition onto corrected113 source; no runtime authority.
"""
from pathlib import Path
import hashlib,json,re,itertools,difflib,importlib.util,shutil,ast
P=Path(__file__).resolve().parent;E=P.parent
B=E/'current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/final-scope-source-1'
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
H=E/'m14-f02-verbose32-host-preparation-source-1/joint-retain-linker-correction-source-1/independent-actual-review-1/REVIEW.json'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,t):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
def js(n,x):save(n,json.dumps(x,indent=2)+'\n')
baseprofile=json.loads((B/'PROFILE.SOURCE-ONLY.json').read_text());profile=json.loads(json.dumps(baseprofile));host=json.loads(H.read_text());assert host['decision']=='PASS_ACTUAL_GLOBAL32_HOST_QUALIFICATION_ONLY_LOCAL14_C_RETAINED'
assert ref(N/'READY.SOURCE-ONLY.json')['sha256']=='e7d77b16826fb96189c35a07f444157eadbc75e3290b618bbd4c24451c0cbd9c'
post={r['relative']:r for r in profile['inputs']['postimages']};source=Path(post['kernel/process.c']['postimage']['path']);original=source.read_text().splitlines(True);text=''.join(original)
rows=json.loads((N/'EXACT46-SLOT78-MAP.json').read_text());selected=[r for r in rows if not r['local']];assert len(selected)==32
# Exact existing descriptor blocks; current113 scalar/F06 source remains untouched.
nbase=(N/'base/kernel/process.c').read_text().splitlines(True);translated=[]
for row in selected:
 old=''.join(nbase[row['physical_first']-1:row['physical_after']-1]);assert text.count(old)==1,row['name'];at=text.index(old);first=text[:at].count('\n');after=first+old.count('\n');translated.append((first,after,row))
translated.sort();postlines=[];origins=[];cursor=0
for first,after,row in translated:
 postlines+=original[cursor:first];origins+=list(range(cursor,first));prefix='#ifdef MCKERNEL_RUST_PROCESS_VERBOSE_DATA\n'
 if cursor==0:
  prefix+='''#if !defined(MCKERNEL_RUST_PROCESS_HELPERS) || \\
    !defined(MCKERNEL_PROCESS_DDEBUG_FLAGS) || !defined(MCKERNEL_PROCESS_DDEBUG_FILE)
#error "process verbose storage requires paired Rust/build inputs"
#endif
_Static_assert(DDEBUG_DEFAULT == MCKERNEL_PROCESS_DDEBUG_FLAGS,
    "Rust process debug flags must match C DDEBUG_DEFAULT");
_Static_assert(__builtin_strcmp(__FILE__, MCKERNEL_PROCESS_DDEBUG_FILE) == 0,
    "Rust process debug filename must match actual C __FILE__");
'''
 prefix+='extern struct ddebug '+row['name']+('['+str(row['slots'])+']' if row['array'] else '')+';\n#else\n#line '+str(row['logical_first'])+'\n';suffix='#endif\n#line '+str(row['logical_after'])+'\n'
 postlines+=prefix.splitlines(True);origins += [None]*len(prefix.splitlines(True));postlines+=original[first:after];origins+=list(range(first,after));postlines+=suffix.splitlines(True);origins += [None]*len(suffix.splitlines(True));cursor=after
postlines+=original[cursor:];origins+=list(range(cursor,len(original)))
s=importlib.util.spec_from_file_location('existing_known_guard_checker',N/'check_source.py');checker=importlib.util.module_from_spec(s);s.loader.exec_module(checker)
# Reuse foreground's affected-outer-guard restore rule on the corrected113 input.
stack=[];affected=set();closes=set();starts={a for a,_,_ in translated}
for index,line in enumerate(original):
 if re.match(r'^#if',line):stack.append(index)
 if index in starts:affected.add(stack[0])
 if line.startswith('#else') and len(stack)==1 and stack[0] in affected:closes.add(index)
 if line.startswith('#endif'):
  first=stack.pop()
  if first in affected:closes.add(index)
vars=['MCKERNEL_RUST_PROCESS_HELPERS','MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE','ENABLE_TOFU','PROFILE_ENABLE','ARCH_FAST_MEMSET','DEBUG_PRINT_PROCESS']
fixed={a[2:].split('=',1)[0] for a in json.loads((N/'CURRENT111-C-COMMAND.json').read_text())['command']['argv'] if a.startswith('-D')}
profiles=[]
for bits in itertools.product((False,True),repeat=6):
 defs=(fixed-set(vars))|{k for k,v in zip(vars,bits) if v};profiles.append(dict(bits=bits,defs=defs,ids=checker.identities(original,defs)))
new=[];neworigins=[];resets=[]
for line,origin in zip(postlines,origins):
 new.append(line);neworigins.append(origin)
 if origin in closes:
  targets={}
  for helpers in [False,True]:
   vals={p['ids'][origin+1][:2] for p in profiles if p['bits'][0]==helpers};assert len(vals)==1,(origin,helpers,vals);number,token=vals.pop();assert token is None;targets[helpers]=number
  if targets[False]==targets[True]:reset='#line '+str(targets[True])+'\n'
  else:reset='#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n#line '+str(targets[True]-3)+'\n#else\n#line '+str(targets[False]-1)+'\n#endif\n'
  new+=reset.splitlines(True);neworigins += [None]*len(reset.splitlines(True));resets.append(dict(original_physical=origin+1,reset=reset))
postlines,origins=new,neworigins
# Both active source variants; all original C content except selected32 definitions
# must retain truthful current113 FILE/LINE and bytes, including scalar correction.
controls=[];checked=0
for p in profiles:
 for verbose in [False,True]:
  if verbose and not p['bits'][0]:continue
  defs=set(p['defs'])|{'MCKERNEL_PROCESS_DDEBUG_FLAGS','MCKERNEL_PROCESS_DDEBUG_FILE'}
  if verbose:defs.add('MCKERNEL_RUST_PROCESS_VERBOSE_DATA')
  ids=checker.identities(postlines,defs)
  for index,origin in enumerate(origins):
   if origin is not None:
    assert postlines[index]==original[origin]
    if p['ids'][origin][2] and ids[index][2] and not re.match(r'^\s*#(?:if|else|endif|line)\b',original[origin]):assert p['ids'][origin][:2]==ids[index][:2],(origin+1,original[origin],p['bits'],verbose,p['ids'][origin],ids[index]);checked+=1
  controls.append(dict(zip(vars,p['bits']),verbose=verbose))
assert [x for x in origins if x is not None]==list(range(len(original)))
save('candidate/kernel/process.c',''.join(postlines));save('patches/process.c.diff',''.join(difflib.unified_diff(original,postlines,fromfile='corrected113/kernel/process.c',tofile='next114/kernel/process.c')));js('C-LINE-ORIGINS.json',origins)
# Exactly four existing CMake insertions, rebased on corrected113's newer source.
cm=Path(post['kernel/CMakeLists.txt']['postimage']['path']);basecm=cm.read_text();composed=basecm;nb=(N/'base/kernel/CMakeLists.txt').read_text().splitlines(True);np=(N/'postimage/kernel/CMakeLists.txt').read_text().splitlines(True);ops=[]
for tag,i,j,k,l in difflib.SequenceMatcher(a=nb,b=np,autojunk=False).get_opcodes():
 if tag=='equal':continue
 assert tag=='insert';anchor=''.join(nb[max(0,i-3):i]);addition=''.join(np[k:l]);assert composed.count(anchor)==1;composed=composed.replace(anchor,anchor+addition,1);ops.append(dict(anchor=anchor,addition=addition))
assert len(ops)==4;save('candidate/kernel/CMakeLists.txt',composed);save('patches/CMakeLists.txt.diff',''.join(difflib.unified_diff(basecm.splitlines(True),composed.splitlines(True),fromfile='corrected113/kernel/CMakeLists.txt',tofile='next114/kernel/CMakeLists.txt')))
# Closed119file Rust snapshot: all118 predecessor files byte-preserved except lib.
oldmap=json.loads(Path(profile['inputs']['source_directory_exports'][0]['manifest']['path']).read_text());newmap=json.loads(json.dumps(oldmap));newmap.update(export_root=str(P/'rust-subtree'),predecessor_manifest=ref(Path(profile['inputs']['source_directory_exports'][0]['manifest']['path'])))
newfiles=[]
for row in oldmap['files']:
 old=Path(row['snapshot']['path']);assert ref(old)==row['snapshot'];dest=P/'rust-subtree'/row['relative'];dest.parent.mkdir(parents=True,exist_ok=True);data=old.read_bytes()
 if row['relative']=='lib.rs':
  data=data.replace(b'mod process_helpers;\n',b'mod process_helpers;\n#[cfg(process_verbose_data)]\npub(crate) mod process_verbose_data;\n',1);assert data!=old.read_bytes()
 dest.write_bytes(data);nr=json.loads(json.dumps(row));nr['predecessor_snapshot']=row['snapshot'];nr['snapshot']=ref(dest);nr['kind']='unchanged corrected113 source' if data==old.read_bytes() else 'existing foreground verbose32 module selection';newfiles.append(nr)
dest=P/'rust-subtree/process_verbose_data.rs';dest.write_bytes((N/'postimage/kernel/rust/process_verbose_data.rs').read_bytes());newfiles.append(dict(relative='process_verbose_data.rs',original=ref(N/'postimage/kernel/rust/process_verbose_data.rs'),snapshot=ref(dest),kind='exact HOST-qualified existing global32 storage;LOCAL14 disabled'))
newmap['files']=sorted(newfiles,key=lambda x:x['relative']);newmap['total_bytes']=sum(x['snapshot']['bytes'] for x in newfiles);newmap['new_leaf_files']=list(set(oldmap.get('new_leaf_files',[]))|{'process_verbose_data.rs'});js('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',newmap)
# Literal production commands add only matching32 storage env/cfg/C definitions.
rustargv=profile['exact_commands'][0]['argv'];idx=rustargv.index('/nightly/bin/rustc');rustargv[idx:idx]=['MCKERNEL_PROCESS_C_FILE=/src/kernel/process.c','MCKERNEL_PROCESS_DDEBUG_FLAGS=0'];rustargv[-1:-1]=['--cfg','process_verbose_data']
cargv=profile['exact_commands'][1]['argv'];cargv[1:1]=['-DMCKERNEL_RUST_PROCESS_VERBOSE_DATA','-DMCKERNEL_PROCESS_DDEBUG_FLAGS=0','-DMCKERNEL_PROCESS_DDEBUG_FILE="/src/kernel/process.c"']
for relative in ['kernel/CMakeLists.txt','kernel/process.c']:
 post[relative]['postimage']=ref(P/'candidate'/relative)
profile['inputs']['postimages']=list(post.values());profile['inputs']['source_directory_exports']=[dict(host_path=str(P/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in newmap['files']]
profile.update(status='NEXT114_PRIVATE_DEBUG32_ON_CORRECTED113_SOURCE_ONLY_NOT_ADOPTED_NOT_RELEASED',request_sha256=None,actual_nonce=None,actual_root_adoption=None,actual_execution_review=None,actual_resource_authority=None,actual_output_root=None,actual_holder=None,native_custody_clearance=None,reuse_descriptor=str(P/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json'))
contract=profile['producer_contract'];contract['source']='Exact corrected113 planned scalar4/F06next4 source plus actual HOST-qualified existing verbose32 data; CURRENT113 and114 actual/default acceptance are not inferred.';contract['process_delta']+=' Plus exact existing foreground32GLOBAL/64slot/2048B debug owner migration; expected63->31C OBJECTs, LOCAL14 retainedC. No config/local14 ownership changes.';contract['expected_process_OBJECT_records']=31;contract['expected_new_Rust_data']+= [r['name'] for r in selected];contract['postbuild_required'] += ['Actual source tuple/flags prove default process_verbose_data cfg and paired C selector, mandatory actualCargvfilename env/Cassert and defaultflags0 on all32 globals; flags1 HOST scope only because inherited scalar4 rejects DEBUG_PRINT_PROCESS selected variant.','Exactly32originalglobal Cmetadataobjects absent, same32Rustowners unique GLOBAL writable __verbose GNU_RETAIN/8alignment/64slots/2048B;14CLOCAL/configs retained and total78slots unchanged; alloriginalarrays/FILE/FUNC/FMT/LINE/flags/padding/156R64 content and originalcurrentrawconsumers qualified.','FinalproductionGNUld2.41 retains all RustGNU_RETAIN bits, no useofHostld2.34; registryboundary/stride/ordering/traversal and exactcurrentconsumer/pointertargets bound to newimage.','OriginalHOSTfailureHostld2.34Rloss preserved; correctedLLVM21HOSTacceptance11d85a1b reused withoutcompile/negativecontrol replay. No local14/46wholefile/nativeclaim.']
profile['qualified_verbose32_actual_HOST']=ref(H);profile['verbose32_foreground_source']=ref(N/'READY.SOURCE-ONLY.json');profile['next114_source_base']=ref(B/'SOURCE-READY.json');profile['source_preparation_current_context']=dict(runtime_authority=None,parent_supplied_Root_ledger='Root36/4534',parent_supplied_current_free_prefix='85ce',actual_fresh_admission_and_ownership_required=True)
profile['origin_source_materialization']['status']='UNCHANGED_CORRECTED113_ARCH_SOURCE_ARGV_ROOT_BINDS_MATCHING_ACTUAL113_ORIGIN_NO_AUTOMATIC_REPLAY';profile['origin_source_materialization']['unchanged_113_arch_command']=True
js('PROFILE.SOURCE-ONLY.json',profile);js('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',dict(scope=profile['scope'],runtime_authority=None,status='NEXT114_SOURCE_ONLY_FOUR_COMMANDS_NOT_RELEASED',commands=profile['exact_commands'],new_objects=3,retained_objects=8,link_inputs=11,LOCAL14_selected=False))
reuse=json.loads(Path(baseprofile['reuse_descriptor']).read_text());reuse['source_successor_profile']=ref(P/'PROFILE.SOURCE-ONLY.json');reuse['planned_source_only_next114']=True;js('FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json',reuse)
export=json.loads((B/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json').read_text());export.update(status='NEXT114_DEBUG32_EXPORT_TEMPLATE_NOT_AUTHORITY',runtime_authority=None,request_sha256=None,author=None,decision=None);export['qualified_readonly_files']=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in profile['inputs']['postimages']]+[r['snapshot'] for r in newmap['files']];js('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
# Existing exact machinery is copied byte-for-byte; no new execution path/gate.
tools=[]
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 data=(B/name).read_bytes();(P/name).write_bytes(data);ast.parse(data);tools.append(dict(predecessor=ref(B/name),successor=ref(P/name),byte_identical=True))
s=importlib.util.spec_from_file_location('retained_build_source',P/'run_build_only.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner);assert runner.source_directory_postimages(profile)==[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in newmap['files']]
js('COMPOSITION-DERIVATION.json',dict(scope=profile['scope'],runtime_authority=None,planned_corrected113_base=ref(B/'SOURCE-READY.json'),foreground_ready=ref(N/'READY.SOURCE-ONLY.json'),actual_HOST=ref(H),C_base=ref(source),C_post=ref(P/'candidate/kernel/process.c'),CMake_base=ref(cm),CMake_insertions=ops,source_controls=controls,active_original_identity_checks=checked,outer_guard_restores=resets,Rust_previous_files=118,Rust_current_files=119,Rust_existing_storage_unmodified=ref(dest),LOCAL14_C_retained=True,all_config_source_unchanged=True,actual_build_release=False))
ready=dict(scope=profile['scope'],status='NEXT114_SOURCE_READY_ON_PLANNED_CORRECTED113_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None,profile=ref(P/'PROFILE.SOURCE-ONLY.json'),commands=ref(P/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json'),export=ref(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),source_map=ref(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),composition=ref(P/'COMPOSITION-DERIVATION.json'),actual_HOST=ref(H),tools=tools,commands_count=4,new_objects=3,retained_objects=8,source_controls=len(controls),expected_process_C_objects=31,expected_C_functions=83,expected_Rust_function_exports=56,counts_unaccepted=True,LOCAL14_selected=False,compiler_workload_guard_resources_canonical_Git_operations=0)
js('SOURCE-READY.json',ready);print(json.dumps(dict(status=ready['status'],profile=ready['profile'],controls=len(controls),Rust_files=119,compiler_workloads=0)))
