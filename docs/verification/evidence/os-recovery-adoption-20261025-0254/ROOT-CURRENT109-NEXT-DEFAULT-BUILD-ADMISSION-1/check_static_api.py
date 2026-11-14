"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Literal existing API/source closure preflight; no current capture or execution.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,inspect,json
D=Path(__file__).resolve().parent;E=D.parent;Q=E/'qualified-current26eb-next-default-source-1'
def read(p):return json.loads(p.read_text())
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 facts=read(D/'ROOT-STATIC-FINALIZATION-INPUTS.NOT-AUTHORITY.json');P=read(D/'PROFILE.TEMPLATE.NOT-RELEASED.json');export=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')
 for name,row in facts['tool_sources'].items():assert ref(D/name)==row['local'] and (D/name).read_bytes()==Path(row['source']['path']).read_bytes();ast.parse((D/name).read_text())
 assert (D/'PROFILE.TEMPLATE.NOT-RELEASED.json').read_bytes()==(Q/'PROFILE.SOURCE-ONLY.json').read_bytes()
 assert (D/'check_postbuild_current.py').read_bytes()==(Q/'check_postbuild_current.py').read_bytes()
 runner=module('exact_fixed_five_static_API',D/'run_build_only.py');publisher=module('existing_exact_publisher_API',D/'publish_approved_ready.py')
 assert list(inspect.signature(publisher.publish).parameters)==['preparation','approved_input_sha']
 vector=copy.deepcopy(P);vector['request_sha256']='a'*64;assert len(runner.commands_for_plan(vector))==5
 rows=runner.source_directory_postimages(P);assert len(rows)==109
 refs=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in rows]
 assert refs==export['qualified_readonly_files']
 for row in refs:runner.auth(row)
 synthetic=D/'OUTPUT-PURE-API-NOT-CREATED';mounts=runner.mounts(P,export,synthetic);assert len({r['target'] for r in mounts})==len(mounts);assert [r for r in mounts if r['target']=='/src/kernel/rust']==[dict(host=P['inputs']['source_directory_exports'][0]['host_path'],target='/src/kernel/rust',readonly=True)]
 argv=runner.docker_argv(P,'pure-no-launch-fixed-five',mounts,synthetic);assert argv[:4]==runner.SUDO_DOCKER_PREFIX and argv[-4:]==['-I','-B','/build-only-worker.py','/build-only-plan.json']
 assert sum(not r['replace'] for r in P['inputs']['objects'])==7 and sum(r['replace'] for r in P['inputs']['objects'])==4
 assert P['request_sha256'] is None and P['native_custody_clearance'] is None and P['runtime_authority'] is None
 # The resource helper's top level performs real capture: never import it here.
 # Its exact existing AST must rebind every actual identity after Root bootstrap.
 tree=ast.parse((D/'capture_and_bind_resource.py').read_text());updates={}
 for n in ast.walk(tree):
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='update' and isinstance(n.func.value,ast.Name):updates[n.func.value.id]={k.arg for k in n.keywords}
 assert {'nonce','observed_at_epoch','observed_clocks','reservation_owner','reservation_holder','fresh_output_root','native_custody_clearance','reservation_ready_record'}<=updates['resource']
 assert {'nonce','runner','worker','profile','review','resource_authority','input_export_authority','fresh_output_root','native_custody_clearance'}<=updates['grant']
 for name in ['ROOT-HOLDER-BOOTSTRAP.TEMPLATE.NOT-GRANTED.json','ROOT-EXECUTION-INPUT.TEMPLATE.NOT-GRANTED.json','INDEPENDENT-EXECUTION-REVIEW.SCHEMA-NOT-REVIEW.json','ROOT-RESOURCE.SCHEMA-NOT-AUTHORITY.json']:
  x=read(D/name);assert x['nonce'] is None and x['native_custody_clearance'] is None
  for key in ['fresh_handshake_root','fresh_output_root']:
   if key in x:assert x[key] is None
 request=read(D/'STATIC-REQUEST-PAYLOAD.TEMPLATE.NOT-AUTHORITY.json');assert all(request[k] is None for k in ['nonce','current_physical_clearance','actual_output_root','actual_handshake_root','actual_holder','actual_resource_clock','actual_resource_authority','actual_execution_review','actual_grant'])
 assert request['source_adoption']==ref(Q/'ROOT-CANONICAL-SOURCE-ADOPTION.json') and request['independent_source_profile_review']==ref(Q/'ROOT-RECORDED-INDEPENDENT-SOURCE-PROFILE-REVIEW.json')
 ast.parse((D/'finalize_static_for_root.py').read_text());assert not synthetic.exists() and not (D/'HOLDER').exists() and not (D/'OUTPUT').exists() and not (D/'PROFILE.SOURCE-ONLY.json').exists()
 report=dict(scope=__doc__.splitlines()[0],status='PASS_REAL_FIXED_FIVE_API_7_PREFIX_109_RUST_EXPORT_CLOSURE_AND_NULL_ACTUAL_BINDINGS',runtime_authority=None,profile_template=ref(D/'PROFILE.TEMPLATE.NOT-RELEASED.json'),byteexact_tools=5,commands=5,retained_C_inputs=7,new_objects=4,closed_Rust_files=109,exact_raw_ld_inputs=11,resource_helper_actual_rebindings_verified=True,resource_helper_never_imported=True,physical_clearance=None,source_adoption=request['source_adoption'],actual_nonce=None,actual_output_root=None,actual_holder_clock_grant_created=False,compiler_Docker_canonical_Git_actions=0)
 (D/'LITERAL-API-PREFLIGHT.SOURCE-ONLY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
