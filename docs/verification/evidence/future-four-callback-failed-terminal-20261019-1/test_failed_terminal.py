"""One affected ordinary consumer fixture; no root, Docker or cleanup execution."""
from pathlib import Path
import ast,copy,hashlib,json,os,types
F=Path(__file__).resolve().parent
OUTPUT=F/'affected-failure-fixture-1'
def load(name):
 p=F/name;m=types.ModuleType(name);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def need(ok,why):
 if not ok:raise RuntimeError(why)
def refused(f):
 try:f()
 except (RuntimeError,AssertionError,KeyError,ValueError):return
 raise RuntimeError('expected refusal')
def fns(p):
 t=ast.parse(p.read_text());return {n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def main():
 need(os.getuid()==os.geteuid()==1000,'ordinary fixture only');need(not OUTPUT.exists(),'fresh fixture output')
 gate=load('failed_operation_authority.py');cleanup=load('cleanup_failed.py');obs=load('observe_failed_retirement.py');readback=load('readback_observer.py');checks=[]
 # Real root/runtime entrypoints must reject ordinary execution before effects.
 refused(lambda:obs.main(['--git-commit','0'*40,'--git-tree','0'*40,'--observation-release','/nonexistent','--observation-release-sha256','0'*64,'--failed-authority-sha256','0'*64]));checks.append('actual observer ordinary refusal')
 need(not obs.OUTPUT.exists(),'no root outputs created')
 authority=json.loads((F/'FAILED-BUILD-PRESERVATION-AUTHORITY.json').read_bytes());gate.validate_failure_authority(authority);checks.append('actual independent failure preservation authority')
 for key in ['cleanup_authorized','production_image_acceptance','native_acceptance','compute_C_retirement','physical_release']:
  bad=copy.deepcopy(authority);bad[key]=True;refused(lambda:gate.validate_failure_authority(bad))
 checks.append('five acceptance/release widening refusals')
 pairs=gate.verify(authority['retained_logs']['pairs'],True);obs.fp_contract().authority_pairs(pairs,obs.FOURLEAF_ROLES);refused(lambda:obs.fp_contract().authority_pairs(pairs[:-1],obs.FOURLEAF_ROLES));checks.append('actual eleven roles and omitted role refusal')
 rows=[obs.new_object_binding(cleanup,pair[key]) for pair in pairs for key in ('original','retained')];need(len(rows)==2*len(pairs),'all FD rows');checks.append('actual twenty-two original/retained FD rows')
 owner=gate.verify(authority['owner_receipt'],True);guard=gate.verify(authority['guard_result'],True);inspection=owner['terminal_container_info'];physical=json.loads((F/'actual-failed-physical-bindings.json').read_bytes());target=dict(physical['target'],image_id=inspection['Image'],exit_code=1)
 cleanup.image_request_binding(gate.verify(authority['source11']['request'],True));cleanup.image_receipt_binding(owner,guard,target,inspection,authority['owner_receipt']['sha256']);checks.append('actual generic request plus failed owner/guard consumer')
 bad=copy.deepcopy(target);bad['exit_code']=0;refused(lambda:cleanup.image_receipt_binding(owner,guard,bad,inspection,authority['owner_receipt']['sha256']));checks.append('success exit substitution refusal')
 selected={authority['source11'][key]['path']:dict(sha256=authority['source11'][key]['sha256']) for key in ('request','materialization','fullsource','additional_dispatcher','toolchain','provenance')};selected[str(F/'FAILED-BUILD-PRESERVATION-AUTHORITY.json')]=dict(sha256=hashlib.sha256((F/'FAILED-BUILD-PRESERVATION-AUTHORITY.json').read_bytes()).hexdigest())
 cleanup.typed_source_binding(gate.verify(authority['source11']['request'],True),dict(candidate_root=dict(inode=48005996)),selected);checks.append('actual failure typed source consumer')
 bad=copy.deepcopy(pairs[0]['original']);bad['inode']+=1;refused(lambda:gate.verify(bad));checks.append('represented FD inode refusal')
 core=Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py');a=fns(core);b=fns(F/'cleanup_failed.py');changed=[k for k in a if a[k]!=b[k]];need(set(changed)=={'typed_source_binding','prepare_release','configure'},'only case source gate and author changed');old='native-rust-fp-release-image-guard-20261018-9582bfa72e354a06810bed72e3e36a71';new=obs.CAPTURE.name;need(a['configure'].replace(old,new)==b['configure'],'configure only guard basename delta');checks.append('generic lifetime/census/transaction AST unchanged')
 post=ast.parse((F/'postjoin_readback.py').read_text());need(not any(isinstance(n,ast.Constant) and n.value in (21,29,42,58) for n in ast.walk(post)),'no stale FD cardinality');checks.append('postjoin derives count from actual pairlist')
 need(readback.NONCE==obs.NONCE and readback.OUTPUT==obs.OUTPUT and len(readback.NAMES)==5,'five originals distinct summary contract');checks.append('raw five output contract')
 OUTPUT.mkdir();(OUTPUT/'result.json').write_text(json.dumps(dict(status='PASS_AFFECTED_FAILURE_TERMINAL_FIXTURE_ONLY',checks=checks,check_count=len(checks),retained_pairs=len(pairs),fd_rows=len(rows),root_executed=False,cleanup_executed=False),sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status='PASS_AFFECTED_FAILURE_TERMINAL_FIXTURE_ONLY',checks=len(checks),retained_pairs=len(pairs),fd_rows=len(rows))))
if __name__=='__main__':main()
