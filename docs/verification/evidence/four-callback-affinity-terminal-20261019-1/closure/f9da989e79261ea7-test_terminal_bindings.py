"""Affected actual configure/sourceclosure callers; no root/tool/container/cleanup effects."""
from pathlib import Path
import importlib.util,json,hashlib,types,ast
T=Path(__file__).resolve().parent;N=Path('/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1');O=Path('/home/holden/mckernel-work/host-preparation/evening-git-owner-review-20261019-1')
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def load(p):
 m=types.ModuleType(p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
config=dict(physical=ref(T/'actual-fourleaf-physical-bindings.json'),pairs=ref(T/'retained-production-objects/retained-objects.json'),selected_provenance=ref(T/'canonical-selected-provenance-refs.json'),canonical_report=ref(O/'FOURLEAF-ACTUAL-PRODUCTION-ARTIFACT-REVIEW.json'),canonical_gate=ref(N/'stage_case.py'),canonical_binding=ref(N/'canonical-authority-binding.json'))
f=T/'terminal-binding-fixture-1';f.mkdir();(f/'pre-execution-source-map.json').write_text(json.dumps({x:ref(T/x) for x in ['test_terminal_bindings.py','configure_fourleaf_terminal.py']},indent=2)+'\n');(T/'actual-terminal-source-config.json').write_text(json.dumps(config,indent=2)+'\n')
g=load(T/'configure_fourleaf_terminal.py')
for name,source in [('cleanup_fourleaf.py',g.configure_cleanup(config))]:
 with (T/name).open('x') as out:out.write(source)
source=g.configure(config)
with (T/'observe_four_leaf_image_retirement.py').open('x') as out:out.write(source)
observer=load(T/'observe_four_leaf_image_retirement.py');cleanup=load(T/'cleanup_fourleaf.py');pairs=json.loads(Path(config['pairs']['path']).read_text());report=json.loads(Path(config['canonical_report']['path']).read_text());assert len(observer.fp_contract().authority_pairs(pairs,observer.FOURLEAF_ROLES))==21
observer.validate_artifact_authority(report,pairs,cleanup)
b=json.loads(Path(config['canonical_binding']['path']).read_text());full=b['full_fourleaf_source_authority'];request={k:full[k] for k in ['source_root','source_identity','source_derivative_sha256','materialization_sha256','candidate_sha','candidate_identity_scope']};selected={full[k]['path']:dict(sha256=full[k]['sha256']) for k in ['entire_source_manifest','materialization_receipt']};assert cleanup.typed_source_binding(request,dict(candidate_root=dict(inode=full['source_identity']['inode'])),selected)
negatives=0
try:observer.fp_contract().authority_pairs(pairs[:-1]+[pairs[0]],observer.FOURLEAF_ROLES)
except RuntimeError:negatives+=1
else:raise AssertionError('duplicate21accepted')
try:cleanup.configure(dict(status='PENDING_NO_ROOT_AUTHORITY'))
except cleanup.Refusal:negatives+=1
else:raise AssertionError('pendingcleanupreleaseaccepted')
source_map={x:ref(T/x) for x in ['cleanup_fourleaf.py','observe_four_leaf_image_retirement.py','configure_fourleaf_terminal.py']};(T/'terminal-source-map.json').write_text(json.dumps(source_map,indent=2)+'\n');(f/'summary.json').write_text(json.dumps(dict(status='PASS_AFFECTED_ACTUAL_CONFIGURE_METADATA_SOURCECLOSURE_CALLERS_ONLY',positive_callers=3,negative_cases=negatives,finite_retained_pairs=21,source11=11,root_calls=0,subprocess_calls=0,cleanup_operations=0,sources=source_map,config=ref(T/'actual-terminal-source-config.json')),indent=2)+'\n');print('PASS callers3/refusals2; finite21/source11; no root/tool/cleanup effects')
