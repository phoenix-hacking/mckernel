"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite227 ordinary profile and strict result-parser source review; no workload.
"""
from pathlib import Path
import ast,datetime,hashlib,json
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;S=E/'m15-rust-executor-process227-collector-source-1';H=E/'m15-rust-executor-process235-host-preparation-source-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
r=read(P/'READY.json');p=read(P/'BOUND-RECIPE.NOT-GRANTED.json');source=read(P/'SOURCE-INPUTS.NOT-GRANTED.json');api=read(P/'EXISTING-FINITE-API-RECIPE.json');old=read(H/'BOUND-RECIPE.NOT-GRANTED.json');case=read(S/'COLLECTOR-CASEPROFILE.json')
assert ref(P/'READY.json')['sha256']=='702ef46727fe7a56b791d71c35979966a63504a087dad1e381ba3e13fac9252d'
assert ref(P/'BOUND-RECIPE.NOT-GRANTED.json')['sha256']=='e56a1e915c2bb696d6c5bf4e4c8887fa95be3c589a0646be14b185e5f206e8d4'
for row in r['files']:assert ref(row['path'])==row
assert p['source_review']==ref(S/'independent-source-profile-review-1/REVIEW.json') and p['source_review']['sha256']=='b3de6a53d71ba865284da266aa263441bb6dfec328be655a98f50a77c6b7d183'
assert p['caseprofile']==ref(S/'COLLECTOR-CASEPROFILE.json') and p['source_ready']==ref(S/'READY.json')
assert len(p['commands'])==3 and p['resources']==old['resources'] and p['fixed_cutoffs']==old['fixed_cutoffs']
assert p['goal']=='01a17e6f-112f-7660-8771-85d15e07a26c' and p['task_id']=='NEW12H-ORDINARY-HOST-M15-PROCESS227-INTERFACE-1'
out=P/'future-output-1';assert not out.exists() and not Path(p['capture_root']).exists()
for i,c in enumerate(p['commands']):
 assert c['cwd']==str(S) and c['leaf']==p['leaves'][0]['name']
 assert c['argv_compact_json_LF_sha256']==hashlib.sha256((json.dumps(c['argv'],separators=(',',':'))+'\n').encode()).hexdigest()
 if i<2:assert c['argv'][:2]==['/usr/bin/env','TMPDIR='+str(out)] and source['compiler']['path'] in c['argv']
assert p['commands'][1]['argv'][2]=='STARTUP_FAKEEXEC_PATH='+str(out/'process227-fakeexec')
assert p['commands'][0]['argv'][-3:]==[str(S/'fakeexec.rs'),'-o',str(out/'process227-fakeexec')]
assert p['commands'][1]['argv'][-3:]==[str(S/'main.rs'),'-o',str(out/'process227-tests')]
assert p['commands'][2]['argv']==[str(out/'process227-tests'),'--test-threads=1']
assert p['expected_test_names']==old['expected_test_names'] and len(set(p['expected_test_names']))==p['expected_test_count']==26
assert len(p['source_inputs'])==len(p['qualified_generic_source_inputs'])==8
for a,b in zip(p['source_inputs'],p['qualified_generic_source_inputs']):assert Path(a['path']).name==Path(b['path']).name and ref(a['path'])==a and ref(b['path'])==b and a['sha256']==b['sha256']
assert p['expected_stdout_input']==ref(S/'expected.stdout') and p['expected_stdout_input']['bytes']==227 and Path(p['expected_stdout_input']['path']).read_bytes()==bytes.fromhex(case['oracle']['stdout_hex'])
assert p['reused_actual_collector_artifact']==case['qualified_predecessor']['actual_collector'] and p['reused_generic_HOST_qualification']==case['qualified_predecessor']['actual_HOST_review']
for key in ['reused_actual_collector_artifact','reused_generic_HOST_qualification','reused_static_ELF_raw','reused_generic_binding_facts','retained_overlay_source']:assert ref(p[key]['path'])==p[key]
assert p['reused_actual_collector_artifact']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
assert p['production_recompiled'] is p['readelf_replayed'] is False and p['new227_HOST_status']=='UNRUN' and p['Root_grant'] is p['Root_actual_boundary'] is p['new227_test_receipts'] is None
pins={x['path']:x for x in p['inputs']};assert len(pins)==len(p['inputs'])==85
for k in ['runner','admission','capture']:assert api[k]==source[k] and pins[api[k]['path']]==api[k]
assert api['runner']['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34' and api['admission']['sha256']=='7df167b39842976391b6461f831c1a1349e1f3880892c37268579378e8f15a76' and api['capture']['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
# Pure existing profile/input validator only; no main/admission/resource method.
t=ast.parse(Path(api['runner']['path']).read_text());ns=dict(Path=Path,json=json,hashlib=hashlib,THREAD=p['goal'],CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);names={'need','ref','verify','validate_profile'};exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'existing source-only validators','exec'),ns);ns['validate_profile'](p);ns['verify'](p['inputs']+[x['plan'] for x in p['leaves']])
# Parser-only controls are not HOST test executions or new qualification count.
t=ast.parse((P/'check_actual_outputs.py').read_text());cs={};exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','check_tests'}],type_ignores=[]),'strict existing result parser only','exec'),dict(re=__import__('re')),cs)
# Functions need their sibling need() in one shared namespace.
cn=dict(re=__import__('re'));exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','check_tests'}],type_ignores=[]),'strict result parser only','exec'),cn)
names=p['expected_test_names'];valid='running 26 tests\n'+''.join('test '+n+' ... ok\n' for n in names)+'test result: ok. 26 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n'
assert cn['check_tests'](valid.encode(),names) and cn['check_tests'](valid.replace('0.01s','13.2s').encode(),names)
negative=[valid.replace('26 tests','25 tests'),valid.replace('26 passed','25 passed'),valid.replace('0 ignored','1 ignored'),valid.replace('0 filtered out','1 filtered out'),valid.replace('0 measured','1 measured'),valid.replace('test '+names[0]+' ... ok\n',''),valid.replace('test '+names[0]+' ... ok\n','test '+names[1]+' ... ok\n'),valid+'unexpected extra output\n']
for bad in negative:
 try:cn['check_tests'](bad.encode(),names)
 except ValueError:pass
 else:raise AssertionError('invalid test transcript accepted')
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_FINITE_THREE_COMMAND_ORIGINAL227_HOST_PROFILE_GENERIC_ELF_REUSE',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(P/'READY.json'),bound_recipe=ref(P/'BOUND-RECIPE.NOT-GRANTED.json'),source_review=p['source_review'],source_inputs=ref(P/'SOURCE-INPUTS.NOT-GRANTED.json'),finite_API=ref(P/'EXISTING-FINITE-API-RECIPE.json'),source_checker=ref(P/'check_source_profile.py'),actual_output_checker=ref(P/'check_actual_outputs.py'),retained_runtime_primitives={k:api[k] for k in ['runner','admission','capture']},reused_generic_collector=p['reused_actual_collector_artifact'],reused_generic_HOST_review=p['reused_generic_HOST_qualification'],reused_static_ELF_raw=p['reused_static_ELF_raw'],commands=p['commands'],pinned_inputs=85,existing_pure_profile_and85input_validator='PASS; no admission/main',result_parser_controls=dict(positive=2,negative_rejected=8,actual_HOST_tests_executed=0),
findings=['Only three genuine new227 commands are bound: compile HOST-only fakeexec with original227 input, compile the same26 controls with exact STARTUP_FAKEEXEC_PATH, run all26 without filtering using test-threads1. No payload, generic production collector or readelf is recompiled/replayed.',
'All command argv/cwd/leaf/compact-LF hashes, fresh output/capture paths, current thread/task/fixedclocks, source/oracle8-file byteexact closure and85 finite toolchain/runtime/source/helper inputs authenticate. /usr/bin/env explicitly sets TMPDIR and testcompile fakeexec path; actual payload environment remains its original two entries.',
'Qualifiedab3e/c532/static2307 are reused only as generic production source/runtime/argv/env/limits/staticELF evidence. New227 expected.stdout is a HOST test/fakeexec input, not embedded production oracle. Old generic26 actual controls remain separate from new22726 UNRUN; new receipts/grant/boundary stayNULL.',
'Existing6e98/7df/h990 finite API is reused. Root must invoke its reviewed finite methods rather than CLI leafstdout equality; raw test elapsed/readelf evidence is retained. Source pipeline supplies no new runner, quota, execution authority or resource overlap permission.',
'Actual checker requires all3 captured exact command rows, positive0 waits/groups absent/streams closed/no transport errors, empty compiler/test stderr and compiler stdout, exactly26 named ok lines and single summary with zero failures/ignored/measured/filtered. It tolerates only genuine elapsed numeric variation; parser-only controls verify rejection of count changes, omitted/duplicate names, ignored/filtered/measured and extra output.',
'Actual checker also reauthenticates original227 oracle and eight generic source pairs, genuine prior qualified artifact and rawstatic evidence, and calls retained read-only staticELF validation. Only after genuine3command proof does it emit actualnew22726 count; no source plan promotes that count.',
'CPU6/job1/AS2GiB/CPU60/FSIZE64MiB/CORE0/90s, original aggregate7/21.6619,8GiB conservative growth reserve and HOST/scratch/account/boot/clamped deadlines remain unchanged. Fresh Root exclusion/reservations/host headroom and nonce/grant are required even during an unlaunched heavy holder.'],
required_before_execution=['Root exact source/adoption/current-boundary bindings and fresh CPU6 exclusion/account/resources/aggregate planning; no historical235 grant reuse.','Fresh actual Root grant bound to recipee56a/runner6e98 and original fixed lifetime; original stop-signal/capture ownership and per-commandguard/input verification in finite API.'],required_after_execution=['Retain all raw0..2 captures, positive joins, strict26 checker receipt and independent actual case/compiled-input review.','Original227 cancellation/exec/resource-restoration and native/map/source release remain separate; HOSTfakeexec is never staged as mcexec and productionmain is not run on HOST.'],blocking_findings=[],runtime_authority=None,compiler_actions=0,test_payload_workloads=0,guard_or_resource_queries=0,canonical_mutations=0,production_recompiled=False,readelf_replayed=False,new227_actual_control_count=0,native_acceptance=False)
out=D/'REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),commands=3,prepared_controls=26,pinned_inputs=85,blocking_findings=0)))
