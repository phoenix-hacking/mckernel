"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Temporary complete released-schema documents, actual validators/finalizer/prepare.
No dummy authority dicts, validation monkeypatching, real Root data or nonce action.
"""
from pathlib import Path
import contextlib,copy,importlib.util,io,json,sys,tempfile
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('proposed_Root_data_filler',D/'fill_root_source_data.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=[]
def reject(call,label):
 try:call()
 except (ValueError,AssertionError,KeyError):checks.append(label)
 else:raise AssertionError('negative accepted '+label)
q,_=m.inputs();m.actual_capability_checks(q);checks.append('actual released binder.source_check/collector/check5298/29f9/owner APIs pass on original227 retainedbytes')
W=m.E/'new-window-operation-guards-source-20261028-1'
o2=m.read(m.E/'new-window-resume-20261028-1/CURRENT116-OPERATION-2-ALL-CONTROLS/ACCOUNT-GUARD-CONFIG.json');old=m.data(o2['successor'])
with tempfile.TemporaryDirectory(prefix='TEST_ONLY-fullschemas-',dir=D) as td:
 T=Path(td)
 successor=m.read(W/'original227.SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json');successor.update(operation_cutoffs=[1793253600.0,1035705.5689454618,1051043.6959931096],subjects=m.sealing_subjects(),source_owners=['/root','/root/ready227'],minimum_cumulative_spent=old['minimum_cumulative_spent'],guardian=old['guardian'])
 sref=m.write(T/'TEST_ONLY-operation-successor.json',successor)
 review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY_source_fixture',operation='original227',successor=successor)
 rref=m.write(T/'TEST_ONLY-operation-review.json',review)
 config=dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='original227',shared_guard=m.ref(W/'operation_window_guard.py'),successor=sref,review=rref,subjects=m.sealing_subjects())
 cref=m.write(T/'TEST_ONLY-config.json',config)
 # Fixed placeholder tests source syntax only; not generated/reserved/attempted in
 # the actual campaign. The source worker never invokes the Root CLI.
 output=T/'fully-rendered-conditional-documents'
 rendered=m.render('00000000000000000000000000000000',cref,'2026-10-28T07:00:00+00:00',output)
 assert m.validate_generated_documents(rendered)
 checks.append('real filler emits full released227 source/capability/stage/reservation/q schemas; actual capability validators consume them')
 for key in ['source_authority','case_capability','stage_map_acceptance','nonce_reservation']:
  assert rendered[key] is not None and m.data(rendered[key])
 checks.append('all four former Null q fields now exact complete generated document references')
 # Exact reviewed finalizer bytes in a temporary source directory give its normal
 # __file__-based exclusive output path; no validator/global monkeypatching.
 source_dir=T/'exact-reviewed-finalizer';source_dir.mkdir();f=source_dir/'finalize_original227_window_bound.py';f.write_bytes(m.FINALIZER.read_bytes())
 producer=m.module(f,'exact_frozen_finalizer_temporary_effectroot')
 from types import SimpleNamespace
 qref=m.ref(output/'ROOT-FINAL-INPUT.SOURCE-ONLY.json')
 with contextlib.redirect_stdout(io.StringIO()):producer.main(SimpleNamespace(check_template=False,bind_bridge=False,bind_current_observer=False,seal_source_context=True,root_inputs=qref['path'],root_inputs_sha256=qref['sha256']))
 prepare=m.module(producer.F/'prepare_startup_bindings.py','actual_prepare_fullschemas')
 argv=sys.argv;sys.argv=['prepare_startup_bindings.py','--check-static']
 try:
  with contextlib.redirect_stdout(io.StringIO())as out:prepare.main()
 finally:sys.argv=argv
 assert 'PASS_FULL_M15_STARTUP_MANIFEST_AND_LITERAL_OWNER_API_ONLY' in out.getvalue()
 checks.append('REAL frozen53c3 finalizer --seal-source-context→REAL produced prepare --check-static pass complete generatedRoot-doc schemas without dummyrefs or patchedvalidation')
 static=m.read(producer.F/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json');assert static['fixed_cutoffs']==successor['operation_cutoffs']
 assert static['source_authority']==rendered['source_authority'] and static['case_capability']==rendered['case_capability'] and static['stage_map_acceptance']==rendered['stage_map_acceptance'] and static['nonce_reservation']==rendered['nonce_reservation']
 checks.append('generated static preserves exact fullschemaRoot refs and reviewed newclamps')
 cap=m.data(rendered['case_capability'])
 for label,edit in [('wrong payload oracle',lambda c:c['payload']['oracle'].__setitem__('exit_code',1)),('wrong kernel image',lambda c:c['artifacts']['mckernel_image'].__setitem__('sha256','0'*64)),('wrong currentledger',lambda c:c.__setitem__('current_ledger',m.data(q['current_ledger'])['prior_ledger_retained'])),('wrong modules',lambda c:c['modules'].pop()),('runtime release',lambda c:c.__setitem__('runtime_release','GRANTED'))]:
  bad=copy.deepcopy(cap);edit(bad);reject(lambda:m.actual_capability_checks(q,bad),'reject actual capability '+label)
 duplicate=m.data(q['current_ledger'])['consumed_nonces'][-1]
 reject(lambda:m.render(duplicate,cref,'2026-10-28T07:00:00+00:00',T/'must-not-exist'),'reject consumed nonce before any output')
 assert not (T/'must-not-exist').exists()
result=dict(scope=__doc__.splitlines()[0],decision='PASS_TEMPORARY_COMPLETE_RELEASED_ROOT_DOCS_ACTUAL_CAPABILITY_FINALIZER_PREPARE',checks=checks,count=len(checks),validation_monkeypatches=0,dummy_authority_dicts=0,actual_Root_data_created=0,actual_nonce_reservations=0,live_guard_calls=0,runtime_authority=None)
with (D/'REAL-DOCUMENT-CONTROLS-FINAL.json').open('x')as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
