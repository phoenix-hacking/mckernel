"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded whole-registry scope and ordinary-profile schema correction; no operations.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
OLD=P/'callback-target-reader-source-clarification-1'
REVIEW=OLD/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
COUNTER=OLD/'independent-source-profile-review-1/ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json'
RUNNER=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return ref(write(n,json.dumps(x,indent=2)+'\n'))
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
assert ref(REVIEW)['sha256']=='42da9e57262f8c768eaf9abf6dce31f6ceb1f8d1af6f0e8e5f8847eadfd5bea9'
assert ref(COUNTER)['sha256']=='73af30120ba84d74519c6fe7b3c1d0c555b08bacee6328300149153de144bdbd'
counter=read(COUNTER);others=counter['unrelated_retained_records']
assert len(others)==102 and len({r['name'] for r in others})==102 and sum(r['size'] for r in others)==4064
assert counter['actual_existing_objects']==134 and counter['actual_existing_slots']==191 and counter['actual_existing_bytes']==6112
# Retained names/sizes come only from the reviewer's bounded sealed counterexample.
# No old artifact inventory is rerun during preparation.
before=(OLD/'qualify_changed_objects.py').read_text()
text=once(before,'import hashlib,importlib.util,json,re,struct,sys','import copy,hashlib,importlib.util,json,re,struct,sys')
text=once(text,"N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')","N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')\nCOUNTER=Path("+repr(str(COUNTER))+')\nCOUNTER_REF='+repr(ref(COUNTER)))
insert='''def process_metadata(elf,wanted,flags,file,require_retain=False):
 # Original per-record reader unchanged, scoped only to exact process symbol names.
 # Exhaustive whole-container + every unrelated record are separately checked below.
 names={row['name'] for row in wanted}
 view=copy.copy(elf)
 view.symbols=[s for s in elf.symbols if not (s['kind']==1 and 0<s['ndx']<len(elf.sections) and elf.sections[s['ndx']]['name']=='__verbose') or s['name'] in names]
 return m.metadata(view,wanted,flags,file,require_retain)

def verbose_symbols(elf):
 return [s for s in elf.symbols if s['kind']==1 and 0<s['ndx']<len(elf.sections) and elf.sections[s['ndx']]['name']=='__verbose']

def raw_verbose(elf,symbol):
 z=elf.sections[symbol['ndx']]
 assert z['flags']&3==3 and not z['flags']&4 and z['align']>=8 and symbol['value']%8==0 and symbol['size']%32==0
 at=z['off']+symbol['value']-z['addr'];raw=elf.data[at:at+symbol['size']]
 rel={off-symbol['value']:r for off,r in m.relocs(elf,symbol['ndx']).items() if symbol['value']<=off<symbol['value']+symbol['size']}
 assert all(off%32 in (0,8,16) and r[0]==1 for off,r in rel.items())
 return z,raw,rel

def preserve_unrelated(elf,baseline,manifest,label,source_files):
 others=manifest['unrelated_retained_records'];reports=[]
 for row in others:
  old=baseline.definitions(row['name']);new=elf.definitions(row['name'])
  assert len(old)==len(new)==1,(label,row['name'],'unrelated identity')
  old,new=old[0],new[0]
  assert old['kind']==new['kind']==row['type']==1 and old['bind']==new['bind']==row['bind'] and old['size']==new['size']==row['size']
  oz,raw,rel=raw_verbose(baseline,old);nz,nraw,nrel=raw_verbose(elf,new)
  assert (nz['flags']&0x200000)>=(oz['flags']&0x200000),(label,row['name'],'existing GNU_RETAIN')
  assert set(rel)==set(nrel) and normalized_raw(raw,rel)==normalized_raw(nraw,nrel),(label,row['name'],'unrelated packed words/padding/null cells')
  entries=[]
  for off,r in rel.items():
   original=string(baseline,r);actual=string(elf,nrel[off]);origin_binding='literal unchanged'
   if actual!=original:
    # HOST source FILE spelling changes only at the original FILE slot. Function,
    # FMT, words/flags, padding, bindings, sizes, and all record identities stay exact.
    assert off%32==0,(label,row['name'],off,'unrelated FUNC/FMT changed')
    if original=='/src/kernel/process.c':expected=str(D/'candidate/kernel/process.c');origin_binding='exact process C env/source operand'
    else:
     prefix='/src/kernel/rust/';assert original.startswith(prefix),(label,row['name'],original,actual)
     relative=original[len(prefix):];assert relative in source_files
     expected=str(D/'rust-subtree'/relative);origin_binding='exact existing Rust source-directory relocation to HOST source argv'
    assert actual==expected,(label,row['name'],original,actual,expected)
   entries.append(dict(offset=off,original=original,actual=actual,provenance=origin_binding))
  reports.append(dict(name=row['name'],binding=row['bind'],bytes=row['size'],slots=row['size']//32,original_section_index=row['shndx'],actual_section=nz['name'],exact_packed_bytes_and_relocation_positions=True,string_provenance=entries))
 assert len(reports)==102 and sum(r['bytes'] for r in reports)==4064 and sum(r['slots'] for r in reports)==127
 return dict(artifact=ref(elf.path),records=reports,objects=102,slots=127,bytes=4064)

def whole_container(elf,manifest,process_rows,label):
 actual=verbose_symbols(elf);expected={r['name']:r['bytes'] for r in process_rows}
 expected.update({r['name']:r['size'] for r in manifest['unrelated_retained_records']})
 assert len(actual)==148 and len({s['name'] for s in actual})==148
 assert {s['name']:s['size'] for s in actual}==expected,(label,'exact process46 + retained unrelated102')
 assert sum(s['size'] for s in actual)==6560 and sum(s['size']//32 for s in actual)==205
 assert sum(z['size'] for z in elf.sections if z['name']=='__verbose')==6560,(label,'whole registry bytes')
 return dict(label=label,objects=148,slots=205,bytes=6560,process_objects=46,process_slots=78,process_bytes=2496,unrelated_objects=102,unrelated_slots=127,unrelated_bytes=4064)

'''
text=once(text,'def main():\n',insert+'def main():\n')
a=""" registry=[m.metadata(rust,allrows,0,file,True),m.metadata(selected,[],0,file),m.metadata(joint,allrows,0,file,True),m.metadata(fallback,locals,0,file)]
 assert sum(z['size'] for z in joint.sections if z['name']=='__verbose')==2496
"""
b=""" assert ref(COUNTER)==COUNTER_REF;manifest=read(COUNTER)
 assert manifest['retained_actual114_Rust']==proposal['retained_actual114_Rust']
 retained=m.m.Elf(proposal['retained_actual114_Rust']['path'])
 assert len(verbose_symbols(retained))==134 and sum(s['size'] for s in verbose_symbols(retained))==6112
 source_files={r['relative'] for r in read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']}
 registry=[process_metadata(rust,allrows,0,file,True),m.metadata(selected,[],0,file),process_metadata(joint,allrows,0,file,True),m.metadata(fallback,locals,0,file)]
 whole_registry=[whole_container(elf,manifest,allrows,label) for elf,label in [(rust,'selectedRust'),(joint,'selectedjoint'),(offjoint,'optionOFFjoint')]]
 unrelated=[preserve_unrelated(elf,retained,manifest,label,source_files) for elf,label in [(rust,'selectedRust'),(joint,'selectedjoint'),(offjoint,'optionOFFjoint')]]
"""
assert text.count(a)==1;text=text.replace(a,b,1)
text=once(text,'registry=registry,local14_configs=configs','registry=registry,whole_registry=whole_registry,retained102_provenance=unrelated,retained_counterexample=COUNTER_REF,local14_configs=configs')
ast.parse(text);write('qualify_changed_objects.py',text)
write('qualifier-scope-only.diff',''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='frozen347bbd-reader',tofile='process46-plus-retained102-reader')))
# All producer and CPP argv0..5 stay byte-for-byte; only corrected reader path rebinds.
plan=read(OLD/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json');oldargv=[r['argv'][:] for r in plan['commands']]
plan['commands'][6]['argv'][2]=str(D/'qualify_changed_objects.py')
planref=save('EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json',plan)
p=read(OLD/'PROFILE.NOT-GRANTED.json');oldprofile=copy.deepcopy(p)
p['task_id']='NEW12H-ORDINARY-HOST-F02-LOCAL14-CONFIG3-FINAL14-DEFAULT-1'
p['commands'][6]['argv'][2]=str(D/'qualify_changed_objects.py')
for row in p['commands']:
 row.update(cwd=str(P),timeout_seconds=90,stdout_limit_bytes=16384,stderr_limit_bytes=16384,requires_fresh_Root_ordinary_grant=True,leaf=p['leaves'][0]['name'])
 row['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(row['argv'],separators=(',',':'))+'\n').encode()).hexdigest()
assert [row['argv'] for row in p['commands'][:6]]==oldargv[:6]
assert p['commands'][6]['argv'][:2]==oldargv[6][:2] and p['commands'][6]['argv'][3:]==oldargv[6][3:]
p['leaves'][0]['plan']=planref
# Declared capture cap stays original; budget includes eight -o CPP outputs, too.
p['internal_and_capture_bound_bytes'].update(CPP_preprocessed_o_files_max=8*67108864,total=3154116608,headroom_to_4GiB=1140850688)
oldreader=ref(OLD/'qualify_changed_objects.py');oldplan=ref(OLD/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
p['inputs']=[ref(D/'qualify_changed_objects.py') if r==oldreader else planref if r==oldplan else r for r in p['inputs']]
# Exactly one newly discovered lexical tool pin; no tool/lib/source closure walk.
cmake=ref(Path('/usr/bin/cmake'));assert cmake['path'] not in {r['path'] for r in p['inputs']};p['inputs'] += [cmake,ref(COUNTER),ref(REVIEW)]
# Reuse only the original metadata-only validator (no guard/admission/resource methods).
runner_tree=ast.parse(RUNNER.read_text());nodes=[]
for node in runner_tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['THREAD','CUTOFFS'] for t in node.targets):nodes.append(node)
 if isinstance(node,ast.FunctionDef) and node.name in ['need','validate_profile']:nodes.append(node)
ns={'Path':Path,'json':json,'hashlib':hashlib};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(RUNNER),'exec'),ns);ns['validate_profile'](p)
assert p['resources']==oldprofile['resources'] and p['fixed_cutoffs']==oldprofile['fixed_cutoffs'] and p['host_growth_reserve_bytes']==oldprofile['host_growth_reserve_bytes']==4294967296
profileref=save('PROFILE.NOT-GRANTED.json',p)
save('ONE-BOUNDED-CORRECTION.json',dict(scope=SCOPE,runtime_authority=None,original_SOURCE=ref(OLD/'SOURCE-READY.json'),original_profile=ref(OLD/'PROFILE.NOT-GRANTED.json'),independent_blocker=ref(REVIEW),retained_registry_counterexample=ref(COUNTER),correction_count=1,process_cohort=dict(objects=46,slots=78,bytes=2496),retained_unrelated=dict(objects=102,slots=127,bytes=4064,proof='Exact sealed102names/bindings/types/sizes + retained actual object per-record words/nulls/padding/relocationpositions/strings. Only explicit HOST FILE-source spelling rebind allowed; no blind extras accepted.'),whole_new_Rust_and_joint=dict(objects=148,slots=205,bytes=6560),existing_whole_Rust=dict(objects=134,slots=191,bytes=6112),schema_only_corrections=['required NEW12H-ORDINARY-HOST- prefix','original cwd/leaf/timeout/capture/grant metadata fields','original compactJSON-LF argv hashes','exact missing /usr/bin/cmake lexical tool pin'],compiler_CPP_link_argv0_to5_unchanged=True,command6_only_changed_argument='corrected qualifier path',growth_accounting='Added8×64MiB CPP-o files;3,154,116,608B bound within original4GiB,1,140,850,688Bheadroom.',metadata_only_original_validate_profile_PASS=True,source_candidates_ABI_config_consumer_predicates_unchanged=True,default_ON_nondefault_limits_still_OPEN=True,missing_folded_consumer_policy='Unchanged OPEN, never acceptance inference',all_actual_calls=0,no_new_quota=True,no_GLOBAL32_prefix_replay=True))
ready=read(OLD/'SOURCE-READY.json');ready.update(status='ONE_BOUNDED_REGISTRY_SCOPE_AND_ORDINARY_SCHEMA_CORRECTION_SOURCE_READY_NOT_GRANTED',profile=profileref,commands=planref,qualifier_correction=ref(D/'ONE-BOUNDED-CORRECTION.json'),retained_registry_counterexample=ref(COUNTER),existing_metadata_only_profile_validation=True,process_registry=dict(objects=46,slots=78,bytes=2496),whole_registry=dict(objects=148,slots=205,bytes=6560),retained_other_records=102)
save('SOURCE-READY.json',ready)
print(json.dumps(dict(decision='BOUNDED_CORRECTION_SOURCE_READY_NOT_GRANTED',ready=ref(D/'SOURCE-READY.json'),profile=profileref,commands=7,source_changes=0)))
