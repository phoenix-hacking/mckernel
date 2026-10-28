"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One finite metadata-reader suffix; no producer/compiler/semantic/native replay.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).resolve().parent;P=D.parent/'got64-reader-correction-source-1';E=D.parent.parent
Q=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/f06-second-family-qualification-source-1/independent-source-review-1/LOCAL-TARGET-IDENTITY-DIAGNOSIS.json')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
assert ref(Q)['sha256']=='b85001eb8a2de1ac8930cab24a814096fed36c16010c9a447bd51e21aadf5be3'
proof=read(Q);assert proof['counts']==dict(ddebug_descriptors=11,function_literals=2,local_pairs=15,mismatched_edges=19,private_mutable_statics=2)
for r in proof['proof_references'].values():assert ref(r['path'])==r
source=[Path(proof['proof_references'][k]['path']).read_text() for k in ['baseline_source','candidate_source']]
for row in proof['finite_local_target_pairs']:
 if row['kind']=='source_private_mutable_static':assert all(s.count(row['source_declaration'])==1 for s in source)
 for anchor in row.get('source_line_anchors',[]):assert all(anchor['text'] in s for s in source)
cfg=read(P/'READBACK-CONFIG.json');cfg['report_output']=str(D/'READER-output-proposed-1');cfg['finite_local_identity_proof']=ref(Q);put('READBACK-CONFIG.json',cfg)
s=(P/'check_partial.py').read_text();s=s.replace("wanted={'_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}","wanted={'_reuse_elf_owning_relocations','_reuse_elf_object_bytes','_reuse_elf_descriptor','_reuse_elf_cstring'}")
s=s.replace("ns=dict(Path=Path,struct=struct)","ns=dict(Path=Path,struct=struct)")
# Reused exact descriptor helper resolves its existing sibling metadata functions.
s=s.replace("def shape(e,s):\n return [(r['offset'],r['type'],target(e,r)) for r in rels(e,s)]",'''def shape(e,s):
 return [(r['offset'],r['type'],finite_target(e,s,r)) for r in rels(e,s)]''')
needle="base=Elf(O/'baseline.arch.o');candidate=Elf(O/'candidate.arch.o')"
extra='''# Exact expert proof pins the only fifteen local storage identities accepted here.
from finite_local_identity import validate_actual_pairs,mapped_edge,edge_key,synthetic_controls
proof_ref=cfg['finite_local_identity_proof'];proof_raw=Path(proof_ref['path']).read_bytes()
assert len(proof_raw)==proof_ref['bytes'] and hashlib.sha256(proof_raw).hexdigest()==proof_ref['sha256']
proof=json.loads(proof_raw)
assert proof['decision']=='CONFIRMED_FINITE_COMPILER_LOCAL_OBJECT_IDENTITIES' and proof['implementation_ownership'] is False
for reference in proof['proof_references'].values():
 raw=Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
source_texts=[Path(proof['proof_references'][k]['path']).read_text() for k in ['baseline_source','candidate_source']]
for row in proof['finite_local_target_pairs']:
 if row['kind']=='source_private_mutable_static':assert all(text.count(row['source_declaration'])==1 for text in source_texts)
 for anchor in row.get('source_line_anchors',[]):assert all(anchor['text'] in text for text in source_texts)
negative_controls=synthetic_controls(proof)
base=Elf(O/'baseline.arch.o');candidate=Elf(O/'candidate.arch.o')
local_identities=validate_actual_pairs(proof,base,candidate,own,rels,data,ns['_reuse_elf_descriptor'],ns['_reuse_elf_cstring'],allocated)
local_seen={'old':set(),'new':set()}
def finite_target(e,body,r):
 side='old' if e is base else 'new' if e is candidate else None
 if side is not None:
  names={p[side+'_symbol']['name'] for p in proof['finite_local_target_pairs']}
  if r['target']['name'] in names:
   row=mapped_edge(proof['mismatched_relocations'],proof['finite_local_target_pairs'],side,body['name'],r['offset'],r['type'],r['addend'],r['target']['name'])
   local_seen[side].add((body['name'],r['offset'],r['type'],r['addend'],r['target']['name']))
   return ('EXACT_SOURCE_LOCAL_OBJECT_IDENTITY',row['kind'],row['old_symbol']['name'],row['new_symbol']['name'])
 return target(e,r)
'''
assert s.count(needle)==1;s=s.replace(needle,extra,1)
s=s.replace("unchanged=[equal(base,candidate,n) for n in sorted(after)]","unchanged=[equal(base,candidate,n) for n in sorted(after)]\nfor side in ['old','new']:assert local_seen[side]=={edge_key(e,side) for e in proof['mismatched_relocations']},('finite nineteen edges complete',side)")
s=s.replace("unchanged_other_C_bodies=unchanged,","unchanged_other_C_bodies=unchanged,finite_local_target_identity_proof=proof_ref,finite_local_storage_identity=local_identities,finite_local_reference_edges_validated=19,synthetic_metadata_negative_controls=negative_controls,")
ast.parse(s);(D/'check_partial.py').write_text(s);(D/'finite-local-identity-only.diff').write_text(''.join(difflib.unified_diff((P/'check_partial.py').read_text().splitlines(True),s.splitlines(True),fromfile=str(P/'check_partial.py'),tofile=str(D/'check_partial.py'))))
old=read(P/'PROFILE.NOT-GRANTED.json');plan=read(P/'ONE-READER-COMMAND.NOT-GRANTED.json');command=plan['commands'][0];command['id']='readback-exact15-local-identities19-source-bound-edges';command['argv']=['/usr/bin/python3','-B',str(D/'check_partial.py')];command['cwd']=str(D);command['purpose']=__doc__.splitlines()[0]+' Exact expert15localobject/19edge identity proof, finite negative metadata controls, then unchanged18body/provider/consumer checks. No compiler/linker/3640behavior/native replay.';command['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(command['argv'],separators=(',',':'))+'\n').encode()).hexdigest();plan.update(commands=[command],expert_finite_proof=ref(Q),producer_replay=0,actual_nonce=None);put('ONE-READER-COMMAND.NOT-GRANTED.json',plan)
p=old;p.update(task_id='NEW12H-ORDINARY-HOST-F06-SHMGET-EXACT-LOCAL-OBJECT-IDENTITY-READER-1',status='SOURCE_ONLY_ONE_FINITE_LOCAL_IDENTITY_READER_NOT_GRANTED',capture_root=str(D/'future-capture-1'),commands=[command]);p['leaves'][0].update(plan=ref(D/'ONE-READER-COMMAND.NOT-GRANTED.json'),output=str(D/'READER-output-proposed-1'))
inputs={r['path']:r for r in p['inputs']}
for r in [ref(Q)]+list(proof['proof_references'].values()):inputs[r['path']]=r
for path in D.iterdir():
 if path.is_file() and path.name not in ['PROFILE.NOT-GRANTED.json','SOURCE-READY.json']:inputs[str(path)]=ref(path)
p['inputs']=[inputs[k] for k in sorted(inputs)];p['note']='One read-only retained-object suffix only. Finite15namepairs+19bodyoffset/type25/addend0edges; fullstorage/source/staticidentity and descriptor fields validated. No numericcounterrule/genericname/string/bytes/address waiver. All widthbounds/18bodies/uniqueadapterprovider/sys_shmget104 checks retained. Prior two failures and fourproducerobjects immutable.';put('PROFILE.NOT-GRANTED.json',p)
# Source/schema checks only; do not run actual artifact reader or synthetic controls.
import importlib.util
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';spec=importlib.util.spec_from_file_location('existing6e98',runner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_profile(p);m.verify(p['inputs'])
assert not (D/'READER-output-proposed-1').exists() and not (D/'future-capture-1').exists()
put('SOURCE-READY.json',dict(scope=__doc__.splitlines()[0],status='READY_SOURCE_ONLY_EXACT_LOCAL_IDENTITY_READER_SUFFIX_NOT_GRANTED',profile=ref(D/'PROFILE.NOT-GRANTED.json'),reader=ref(D/'check_partial.py'),finite_helper=ref(D/'finite_local_identity.py'),expert_proof=ref(Q),retained_four_objects=cfg['retained_identities'],retained_width_correction=ref(P/'SOURCE-READY.json'),commands_unrun=1,finite_pairs=15,finite_edges=19,pure_negative_controls='PREPARED_UNRUN_IN_SAME_ONE_READER_COMMAND',sourcechecks=['Python_AST','6e98_schema','allpins_exact','sourceanchors_unique_private_declarations','freshoutput_absent'],producer_compiler_linker_semantic_native_replays=0,authority=None))
print(json.dumps(dict(READY=ref(D/'SOURCE-READY.json'),profile=ref(D/'PROFILE.NOT-GRANTED.json'),reader=ref(D/'check_partial.py'),inputs=len(p['inputs']))))
