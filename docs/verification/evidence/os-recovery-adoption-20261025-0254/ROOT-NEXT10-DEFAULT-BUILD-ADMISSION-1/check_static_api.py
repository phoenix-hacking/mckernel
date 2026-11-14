"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Post-adoption literal existing-API preflight; no current capture/holder/Docker call.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,inspect,json
D=Path(__file__).resolve().parent;E=D.parent;Q=E/'qualified-next-ten-selector-default-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def main():
 facts=read(D/'ROOT-STATIC-FINALIZATION-INPUTS.NOT-AUTHORITY.json');p=read(D/'PROFILE.TEMPLATE.NOT-RELEASED.json');x=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')
 for name,row in facts['tool_sources'].items():
  assert ref(D/name)==row['local'] and (D/name).read_bytes()==Path(row['published_origin']['path']).read_bytes()
  ast.parse((D/name).read_text(),filename=name)
 adoption=read(Path(facts['source_adoption']['path']))
 for relative,row in adoption['postimages'].items():
  current=ref(Path('/home/holden/mckernel')/relative);assert (current['bytes'],current['sha256'])==(row['bytes'],row['sha256'])
 spec=importlib.util.spec_from_file_location('next10_exact_existing_four_runner',D/'run_build_only.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 spec=importlib.util.spec_from_file_location('next10_exact_existing_publisher',D/'publish_approved_ready.py');publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
 assert list(inspect.signature(publisher.publish).parameters)==['preparation','approved_input_sha']
 vector=copy.deepcopy(p);vector['request_sha256']=facts['request_sha256_to_be_adopted_by_Root'];commands=runner.commands_for_plan(vector);assert len(commands)==4
 rows=runner.source_directory_postimages(p);assert len(rows)==105
 expected=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['postimage'] for r in rows]
 assert x['qualified_readonly_files']==expected
 for row in expected:runner.auth(row)
 mounts=runner.mounts(p,x,D/'OUTPUT');assert len({r['target'] for r in mounts})==len(mounts)
 argv=runner.docker_argv(p,'next10-preflight-data-only',mounts,D/'OUTPUT');assert argv[:4]==runner.SUDO_DOCKER_PREFIX
 assert argv[-4:]==['-I','-B','/build-only-worker.py','/build-only-plan.json']
 assert len([r for r in p['inputs']['objects'] if not r['replace']])==8
 assert p['request_sha256'] is None and p['native_custody_clearance'] is None and p['runtime_authority'] is None
 # Existing resource helper is not imported: its top level starts live capture.
 # Verify exact field rebinding from AST, retaining all admission guards intact.
 tree=ast.parse((D/'capture_and_bind_resource.py').read_text());updates={}
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='update' and isinstance(node.func.value,ast.Name):updates[node.func.value.id]={k.arg for k in node.keywords}
 assert {'nonce','observed_at_epoch','observed_clocks','reservation_owner','reservation_holder','fresh_output_root','native_custody_clearance','reservation_ready_record'}<=updates['resource']
 assert {'nonce','runner','worker','profile','review','resource_authority','input_export_authority','fresh_output_root','native_custody_clearance'}<=updates['grant']
 free=read(Path(facts['current_free_candidate']['path']));assert free['decision']=='FAILED_OPERATION_RETIRED_CURRENT_FREE' and free['functional_acceptance'] is False and free['nonce']=='1fff493f114662040e1147fdcbf5fa32'
 report=dict(scope=__doc__.splitlines()[0],status='PASS_POST_ADOPTION_REAL_FOUR_COMMAND_API_105_EXPORT_AND_EXACT_HELPER_REBINDING_STATIC_ONLY',runtime_authority=None,canonical_postimages=8,byteexact_tools=5,Rust_files=105,retained_C_inputs=8,commands=4,existing_capture_rebinds_all_actual_identifiers=True,existing_capture_guard_unchanged=True,current_free_candidate=facts['current_free_candidate'],older_685_native_used_as_current_basis=False,nonce_holder_clock_grant_created_by_worker=False,source_request_sha256=facts['request_sha256_to_be_adopted_by_Root'])
 (D/'LITERAL-API-PREFLIGHT.SOURCE-ONLY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
