"""Case-specific specialization of accepted root observer; no root or observation effects."""
from pathlib import Path
import ast,hashlib,json
T=Path(__file__).resolve().parent;R=T.parent.parent;BT=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1');BASE=BT/'populated-source-preparation-1/observe_reset_image_retirement.py'
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def checked(r):
 p=Path(r['path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];return json.loads(raw)
def configure(config):
 physical=checked(config['physical']);pairs=checked(config['pairs']);refs=checked(config['selected_provenance']);assert len(pairs)==21 and len({r['original']['path'] for r in pairs})==21
 authorities=json.loads((T/'actual21-retention-authorities.json').read_text());paths={r['kind']:dict(original=r['original']['path'],retained=r['retained']) for r in authorities};assert len(paths)==21
 for row in authorities:
  matches=[p for p in pairs if p['original']['path']==row['original']['path'] and p['retained']['path']==row['retained']];assert len(matches)==1 and matches[0]['original']==row['original']
 assert physical['target']['container_id']==refs['container_id'] and len(physical['ledger'])==8
 source11=checked(refs['actual_source11']['source11']);full=source11.get('source_sha256',source11);assert len(full)==11
 for p,h in full.items():assert ref(Path(p))['sha256']==h
 cap=Path(physical['guard']['path']).parent;source=BASE.read_text();tree=ast.parse(source);replacements={}
 values=dict(PREP=T,CASE=R,CAPTURE=cap,RETIREMENT=Path(config['physical']['path']),RETIREMENT_SHA=config['physical']['sha256'],OBJECT_AUTHORITY=T/'actual-fourleaf-image-object-authority.json',OBJECT_AUTHORITY_SHA=ref(T/'actual-fourleaf-image-object-authority.json')['sha256'],SOURCE=T/'cleanup_fourleaf.py',SOURCE_SHA=ref(T/'cleanup_fourleaf.py')['sha256'],NONCE='four-leaf-observation-actual-1',BOOT=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),PIDS=tuple(r['pid'] for r in physical['ledger']),NEW_OBJECT_AUTHORITY=Path(config['pairs']['path']),NEW_OBJECT_AUTHORITY_SHA=config['pairs']['sha256'],ARTIFACT_AUTHORITY=Path(config['canonical_report']['path']),ARTIFACT_AUTHORITY_SHA=config['canonical_report']['sha256'],FULL_SOURCE_SHA256=full,FULL_SOURCE_MAP_PATH=Path(refs['actual_source11']['source11']['path']),FULL_SOURCE_MAP_SHA=refs['actual_source11']['source11']['sha256'],TERMINAL_INSPECTION_SHA=physical['terminal_inspection']['sha256'])
 # Immutable source and exact binding gate; missing genuine report hash stays failclosed.
 prelude='\nFOURLEAF_GATE = '+repr(config['canonical_gate'])+'\nFOURLEAF_GATE_BINDING = '+repr(config['canonical_binding'])+'\nFOURLEAF_ROLES = '+repr(paths)+'\n'
 pairfunc='''def fp_contract():
    class Finite21:
        ARTIFACT_ROLES=FOURLEAF_ROLES
        @staticmethod
        def authority_pairs(pairs,roles):
            need(isinstance(pairs,list) and len(pairs)==21,'exact finite21 retained pairs required')
            expected={(r['original'],r['retained']) for r in roles.values()};actual=[]
            for p in pairs:
                need(set(p)=={'original','retained','outside_generic_receipt_inventory'} and p['outside_generic_receipt_inventory'] is True,'exact retained producer pair required')
                a,b=p['original'],p['retained'];need(a['sha256']==b['sha256'] and a['size']==b['size'] and a['nlink']==b['nlink']==1 and (a['device'],a['inode'])!=(b['device'],b['inode']),'independent samebyte retained pair required');actual.append((a['path'],b['path']))
            need(len(set(actual))==21 and set(actual)==expected,'exact finite21 rolepaths required')
            return {k:next(p for p in pairs if p['original']['path']==v['original'] and p['retained']['path']==v['retained']) for k,v in roles.items()}
    return Finite21
'''
 validate='''def validate_artifact_authority(review,new_objects=None,engine=None):
    # Shared exact canonical consumer, independent actual report, no FP renaming.
    raw=stable_bytes(Path(FOURLEAF_GATE['path']),FOURLEAF_GATE['sha256'],4<<20)
    gate=types.ModuleType('_fourleaf_exact_canonical_gate');gate.__file__=FOURLEAF_GATE['path'];exec(compile(raw,gate.__file__,'exec'),gate.__dict__)
    binding=json.loads(stable_bytes(Path(FOURLEAF_GATE_BINDING['path']),FOURLEAF_GATE_BINDING['sha256'],4<<20))
    actual=gate.validate_fourleaf_authority(binding)
    need(actual['path']==str(ARTIFACT_AUTHORITY) and actual['sha256']==ARTIFACT_AUTHORITY_SHA,'exact canonical authority ref differs')
    need(review['schema']=='mckernel.independent-rust-four-leaf-image-actual-review.v1' and review['decision']=='PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT','actual fourleaf canonical authority required')
    fp_contract().authority_pairs(new_objects,FOURLEAF_ROLES)
'''
 lines=source.splitlines(keepends=True)
 for n in tree.body:
  if isinstance(n,ast.FunctionDef) and n.name in ['fp_contract','validate_artifact_authority']:replacements[(n.lineno-1,n.end_lineno)]=pairfunc if n.name=='fp_contract' else validate
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
   key=n.targets[0].id;v=values[key];replacements[(n.lineno-1,n.end_lineno)]=key+' = '+('Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v))+'\n'
 for (start,end),value in sorted(replacements.items(),reverse=True):lines[start:end]=[value]
 source=''.join(lines);source=source.replace("FP_AUTHORITY = Path(",prelude+'\nFP_AUTHORITY = Path(',1)
 # Full-source publication proof is exact source closure; current globalHEAD is irrelevant.
 compile(source,str(T/'observe_four_leaf_image_retirement.py'),'exec')
 return source
def configure_cleanup(config):
 physical=checked(config['physical']);refs=checked(config['selected_provenance']);source=Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py').read_text();tree=ast.parse(source)
 values=dict(NAMESPACE=R,NAMESPACE_ANCESTRY=physical['namespace_ancestry'],NAMESPACE_BINDING=physical['namespace_binding'],PREFIX='four-leaf-terminal-20261019-1',ATTEMPT=R/'common-exclusion.json',REQUEST=R/'image-request.json',LEASE=R/'image-lease.json',OUTPUT=R/'owner-work',EVIDENCE=R/'owner-evidence',KNOWN_TARGET=physical['target'],REQUEST_SHA=refs['source_request_bindings']['request']['sha256'],PUBLISHED_SCRIPT='docs/verification/evidence/evening-fourleaf-terminal-20261019-1/cleanup_fourleaf.py',PUBLISHED_TESTS='scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')
 lines=source.splitlines(keepends=True);replacements={}
 typed="""def typed_source_binding(request,obs,selected_map):
    # Exact shared canonical gate proves fullsource authority; ordinary sourcepaths are historical evidence.
    raw=Path(FOURLEAF_GATE['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FOURLEAF_GATE['sha256']:raise Refusal('fourleaf-gate-source')
    import types
    gate=types.ModuleType('_exact_fourleaf_gate');gate.__file__=FOURLEAF_GATE['path'];exec(compile(raw,gate.__file__,'exec'),gate.__dict__)
    raw=Path(FOURLEAF_GATE_BINDING['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FOURLEAF_GATE_BINDING['sha256']:raise Refusal('fourleaf-gate-binding')
    binding=json.loads(raw);gate.validate_fourleaf_authority(binding);full=binding['full_fourleaf_source_authority']
    for key in ['source_root','source_identity','source_derivative_sha256','materialization_sha256','candidate_sha','candidate_identity_scope']:
        if request[key]!=full[key]:raise Refusal('fourleaf-full-source-'+key)
    if obs['candidate_root']['inode']!=full['source_identity']['inode']:raise Refusal('fourleaf-source-inode')
    for key in ['entire_source_manifest','materialization_receipt']:
        row=full[key]
        if selected_map[row['path']]['sha256']!=row['sha256']:raise Refusal('fourleaf-selected-'+key)
    return True
"""
 for n in tree.body:
  if isinstance(n,ast.FunctionDef) and n.name=='typed_source_binding':replacements[(n.lineno-1,n.end_lineno)]=typed
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
   key=n.targets[0].id;v=values[key];replacements[(n.lineno-1,n.end_lineno)]=key+' = '+('Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v))+'\n'
 for (start,end),value in sorted(replacements.items(),reverse=True):lines[start:end]=[value]
 source=''.join(lines)
 old_guard='native-rust-fp-release-image-guard-20261018-9582bfa72e354a06810bed72e3e36a71';current_guard=Path(physical['guard']['path']).parent.name;assert source.count(old_guard)==2;source=source.replace(old_guard,current_guard)
 prelude='\nFOURLEAF_GATE = '+repr(config['canonical_gate'])+'\nFOURLEAF_GATE_BINDING = '+repr(config['canonical_binding'])+'\n';source=source.replace('REPO = Path(',prelude+'\nREPO = Path(',1);compile(source,str(T/'cleanup_fourleaf.py'),'exec');return source

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--config-sha256',required=True);a.add_argument('--output',required=True);x=a.parse_args();s=configure(checked(dict(path=x.config,sha256=x.config_sha256)));p=Path(x.output)
 with p.open('x') as f:f.write(s)
 print('Configured finite21/sharedcanonical observer source only; rootexecution pending')
