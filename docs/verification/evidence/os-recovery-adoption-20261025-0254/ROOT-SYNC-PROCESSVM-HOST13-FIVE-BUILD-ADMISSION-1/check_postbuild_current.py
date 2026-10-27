"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact data binding around the accepted read-only postjoin observer; no cleanup.
"""
from pathlib import Path
import ast,hashlib,json,re,types
A=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1/check_postbuild_current.py')
SOURCE_SHA256='4cce2989854e74ac0b9faa32292215ba0b140e85211a2ed4762a3855b8266736'
OLD_VALUES={'admission':'ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1','CID':'33ae9294008a13ab890cc3fcbce4c100f8b5c5e95ee27d5d9d3914a2871e7c48','nonce':'2345a19be8fbbc4ed1f4e81c8e94847c','tool':'ROOT-ACTUAL-HOLDER-TOOL65036-RESULT.json','holder_pid':1353039,'holder_start':86396650,'runner_pid':1353536,'runner_start':86400687,'container_name':'/current290-build-only-2345a19be8fbbc4ed1f4e81c8e94847c','status':'PASS_F02_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION'}
def read(path):return json.loads(Path(path).read_text())
def ref(path):
 raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def need(ok,message):
 if not ok:raise RuntimeError(message)
def actual_bindings():
 grant=read(A/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json');nonce=grant['nonce'];need(isinstance(nonce,str) and re.fullmatch('[0-9a-f]{32}',nonce),'actual Root nonce required')
 ready_path=A/'HOLDER/HOLDER.READY.json';ready=read(ready_path);started=read(A/'HOLDER/RUNNER.STARTED.json');joined=read(A/'HOLDER/RUNNER.JOINED.json');terminal=read(A/'HOLDER/BUILD-LOCAL-TERMINAL.json')
 resource_path=Path(grant['resource_authority']['path']);need(ref(resource_path)==grant['resource_authority'],'actual resource bytes changed');resource=read(resource_path)
 need(resource['reservation_ready_record']==ref(ready_path) and resource['reservation_holder']==ready['holder'],'actual same admitted holder')
 need(ready['nonce']==nonce and resource['nonce']==nonce and ready['status']=='ACTUAL_ONE_HEAVY_27_4_HELD_NOT_BUILD_ADMISSION','same actual nonce/holder data')
 need(terminal['holder']==ready['holder'],'same actual terminal holder')
 need(started['pid']==joined['pid'] and started['starttime']==joined['starttime'],'actual started/joined runner identity')
 holder=ready['holder'];need(all(type(v) is int and v>0 for v in [holder['pid'],holder['starttime'],started['pid'],started['starttime']]),'positive actual actor PID/births')
 cid=(A/'OUTPUT/container.cid').read_text().strip();need(re.fullmatch('[0-9a-f]{64}',cid) is not None,'actual captured CID')
 return dict(admission=A.name,CID=cid,nonce=nonce,tool='ROOT-ACTUAL-HOLDER-TOOL-RESULT.json',holder_pid=holder['pid'],holder_start=holder['starttime'],runner_pid=started['pid'],runner_start=started['starttime'],container_name='/current290-build-only-'+nonce,status='PASS_SYNC_PROCESSVM_HOST13_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION')
def bound_observer(values):
 raw=SOURCE.read_bytes();need(hashlib.sha256(raw).hexdigest()==SOURCE_SHA256,'accepted observer source changed')
 need(set(values)==set(OLD_VALUES),'exact finite data substitutions only')
 mapping={(type(old),old):values[name] for name,old in OLD_VALUES.items()};counts={key:0 for key in mapping}
 class Bind(ast.NodeTransformer):
  def visit_Constant(self,node):
   key=(type(node.value),node.value)
   if key in mapping:counts[key]+=1;return ast.copy_location(ast.Constant(value=mapping[key]),node)
   return node
 tree=Bind().visit(ast.parse(raw));need(all(n==1 for n in counts.values()),'exact one literal each; never infer a changed observer')
 module=types.ModuleType('next10_bound_original_postbuild_observer');module.__file__=str(A/'check_postbuild_current.py');exec(compile(ast.fix_missing_locations(tree),str(SOURCE)+':EXACT_DATA_SUBSTITUTIONS_ONLY','exec'),module.__dict__)
 return module,dict(source=ref(SOURCE),original_values=OLD_VALUES,bound_values=values,statement_or_guard_changes=0)
def main():
 observer,binding=bound_observer(actual_bindings());result=observer.observe();result['exact_data_binding']=binding;print(json.dumps(result,indent=2))
if __name__=='__main__':main()
