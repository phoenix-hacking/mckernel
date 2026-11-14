#!/usr/bin/env python3
"""Functional OS only; no security testing. Bounded retained startup diagnosis."""
import hashlib,json,ast,importlib.util
from pathlib import Path
ROOT=Path('/home/holden/mckernel');E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254';OUT=Path(__file__).resolve().parent
L=E/'m15-mcexec-default-f4d-actual-native-preparation-source-1';P=E/'m15-rust-executor-startup-native-entry-source-1'
H=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1')
C=H/'native199-helper-failure-export-1/errno-correction-1';R=E/'f05-causal-rust-supervisor-source-1/compiler-warning-correction-1'
refs={}
def read(label,path,expected=None):
 p=Path(path);a=p.stat();b=p.read_bytes();z=p.stat();assert all(getattr(a,k)==getattr(z,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'));h=hashlib.sha256(b).hexdigest()
 if expected:assert h==expected,(label,h)
 refs[label]={'path':str(p),'sha256':h,'bytes':len(b)};return b

def j(label,p,expected=None):return json.loads(read(label,p,expected))
contract=j('original_native_contract',L/'SOURCE-BOUND-NATIVE-CONTRACT.json')['cases']['startup.argv-empty']
manifest=j('actual_failed_startup_manifest','/home/holden/mckernel-work/scratch/m15st1-inputs/manifest.json','fe20c08172be4cf36f4d62d22bb61525a9edfce018ab28411680b66a205b9f53')
raw=read('be6e_raw_serial',P/'root-adopted-entry-1/independent-actual-native-review-1/serial.native.raw').decode()
frames=[json.loads(z[len('ND_PAYLOAD '):]) for z in raw.splitlines() if z.startswith('ND_PAYLOAD ')]
assert len(frames)==1;failed=frames[0]
assert failed['argv']==['/bin/mcexec','-t','1','0','/apps/app'] and failed['raw_wait_status']==10496
assert bytes.fromhex(failed['streams']['stderr']['hex'])==b'unexpected argc or argv terminator\n'
assert manifest['payload']['argv']==contract['argv'] and manifest['payload']['oracle']==contract['oracle']
assert contract['argv']==['/bin/mcexec','-t','1','0','app','A','','B']
c=read('actual_c020_source',C/'native_diagnostic_guest_collector.helper-diagnostic.c','b3fc4fe0d46ae95a0b428a3c2ff46a8836affc0d929da9a2809cbe3e15b5e2d6').decode()
read('actual_c020_binary',C/'collector-helper-diagnostic','c020a8e0ab43e222caf901d92bfecb2a8d8cf20ea0b539910a17a578f1fd12fc')
cmd=j('actual_c020_compile_command',C/'ordinary-check-1/01-production-static-compile/command.json')
assert '-DND_PROCESS_EXEC_WAIT' in cmd['argv']
assert '#elif defined(ND_FUTEX) || defined(ND_PROCESS_EXEC_WAIT)\nstatic char *const payload_argv[]' in c
assert '"/bin/mcexec", "-t", "1", "0", "/apps/app", NULL' in c
assert '"/bin/mcexec", "-t", "1", "0", "app", "A", "", "B", NULL' in c
read('c020_production_handoff',C/'FINAL-HELPER-DIAGNOSTIC-HANDOFF.json')
overlay=read('actual_overlay_source',H/'native-runtime-ready-1/native_diagnostic_overlay.py','46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d').decode()
ast.parse(overlay);fn=next(n for n in ast.parse(overlay).body if isinstance(n,ast.FunctionDef) and n.name=='build_overlay')
assert not any('argv'==n.id for n in ast.walk(fn) if isinstance(n,ast.Name))
assert '("init", cr, 0o100755)' in overlay
payload=read('original_startup_payload_source','/home/holden/mckernel-work/scratch/stability-packet001-compile-20260913-1/startup.argv-empty/startup.argv-empty.c').decode()
assert 'argc != 4 || argv[argc] != NULL' in payload and 'return 41;' in payload
read('original_startup_payload',contract['payload']['path'],contract['payload']['sha256'])
read('unchanged_full_evaluator',E/'f05-v2-root-export-and-native-preparation-source-1/bound-native-runtime-1/native_diagnostic.py','529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da')
review=j('accepted_Rust_HOST_review',E/'f05-causal-rust-supervisor-host-qualification-1/independent-actual-review-1/REVIEW.json','9b5433a8f3cf35ea159e33d1d342292daa4237eeb1a2f95a5c623370b5bc0e91')
read('accepted_Rust_source_ready',R/'READY.json','81bb4eb14fa872f130fe3c92a7964713eb58115f10505d7845193e5053ec14f6')
read('actual_Rust_collector_artifact',E/'f05-causal-rust-supervisor-host-qualification-1/attempt-2/f05-causal-supervisor','908f147ef0a61959becc20820d6e889aaf5eb4418adda0c99f13b3c3e6cf72a1')
for row in review['selected_seven_Rust_source_closure']:read('Rust_base_'+Path(row['path']).name,row['path'],row['sha256'])
rs=(R/'supervisor.rs').read_text();assert 'mut observer: Option<&mut Observer>' in rs and 'CString::new(*s)' in rs and 'ap.push(std::ptr::null());' in rs
read('working_dca025_provenance',L/'working-c-launcher-dca025-provenance-1/READY.json','c7fe2c2b522bde9c6d387052b6c22f9badb655b3b3d2cf9b2962c92f3018492c')
checks=['Retained actualraw mismatch and10496/exit41 reproduced by reading evidence','Originalpayloadargc4/NULLterminatorpredicate preserved','c020 exactsource/ELF/actual-DND_PROCESS_EXEC_WAIT command join','Compiledprofile picks noargs branch for execution and frame','Overlay does not consume manifestargv and copiescollectorbyteexact','Manifest keeps originalstartup8argv including emptyargument','Originaloracle/streams1024/env/cwd preserved','ActualqualifiedRust81bb/908f seven-source closure matched','Existing Rustsupervise preservesemptyCString and finalNULL pointer','Existingfull evaluator rejects unequal rawargv ratherthan normalizing']
proposal={
 'status':'SOURCE_BOUND_DIAGNOSIS_AND_SEPARATE_RUST_STARTUP_PROFILE_PROPOSAL_NOT_BUILD_OR_NATIVE_RELEASE',
 'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 'actual_failure':{'nonce_prefix':'be6e','raw_payload':failed,'manifest_argv':manifest['payload']['argv'],'meaning':'Collector compiled with process-exec-wait profile launches wrong argv; startup payload returns41 exactly as source requires. Correct startup executor argv has not been exercised; no executor defect established.'},
 'cause':{'source_compile_selector':'-DND_PROCESS_EXEC_WAIT','source_preprocessor_branch':'#elif defined(ND_FUTEX) || defined(ND_PROCESS_EXEC_WAIT)','execution_and_report_literals_both_wrong_for_startup':True,'overlay':'Byte-exact /init copy; no manifestargv serialization or collector runtime configuration exists.','preparation_error':'Earlier native-original-case successor selected c020 without binding its actual compiled caseprofile; staticmanifestargv equality did not prove actualcollectorargv.'},
 'reuse':{'actual_Rust_source_ready':refs['accepted_Rust_source_ready'],'actual_Rust_HOST_review':refs['accepted_Rust_HOST_review'],'actual_existing_artifact':refs['actual_Rust_collector_artifact'],'qualification_scope':'36 ordinary controls and existing F05 Rustcollector source/artifact only; not qualification of proposed startup profile.'},
 'ownership':{'diagnosis_and_proposal':'/root/mcexec_default_prepare, this directory only','future_Rust_implementation':'/root/f05_rust_causal_supervisor after Root assigns new private lane; no implementation copied or edited here','Root':'Independent source adoption, ordinary HOST compile/test/artifact grant, composition+manifest/sourcebinding successor and new native release after positive retirement','F05_current_source_and_native':'Unchanged; no F05 gate/oracle/profile substitution'},
 'exact_successor_profile':{'case_id':'startup.argv-empty','argv':contract['argv'],'env':contract['environment'],'cwd':contract['cwd'],'oracle':contract['oracle'],'payload':contract['payload'],'collector_timeout_seconds':120,'payload_timeout_ms':10000,'stdout_limit_bytes':1024,'stderr_limit_bytes':1024,'frame_limit_bytes':4096,'post_reap_retirement_ms':5000,'supervise_call':'supervise("/bin/mcexec", STARTUP_ARGV, PAYLOAD_ENV, Some("/case/work"), 10_000, outer, None)','startup_boot_argv':['/bin/native-boot'],'original_boot_scope':'Original Cstartup#else bootargv only /bin/native-boot; F05 process profile boot hidos/allow_oversubscribe is a distinct concrete input. Preserve originalstartup unless Root separately reviews and discloses necessary current helper/profile adaptation.'},
 'minimal_source_delta':[
 {'file':'private supervisor.rs','change':'Reuse generic supervisor, pipes, FFI/close/exec/error-pipe/reap/stream/deadline code from exact61bdd82d. Single fixedstartup argv constant: app,A,empty,B. No runtimegenericargv parser, env expansion or shell. Pass None to generic observer slot; do not run F05 causalobserver.'},
 {'file':'private report.rs','change':'Reuse9c55957c wire formatter/1024streams/frameoverflow/oneframe rules; replace ONLY argv header with startup8-element literal, sourced from same fixedprofile. Verify compiledframe and actualchildargv together on HOST.'},
 {'file':'private main.rs','change':'Reuse a5137961 PID1/helpers/modules/printk/evidence/log/poweroff. Startup invokes generic supervise with observerNone. Postreap retain original Cstartup5s monotonic deadline and procfs_empty positive result; no F05 clone/wait/gate/Observer.complete/final_snapshot_covers_observation predicates. Avoid broad warning suppression: omit F05-only lifecycle/observer code from selected startup build or justify exact extraction.'},
 {'file':'private tests','change':'Preserve applicable generic HOST controls and add exactcase tests: actual argv empty element+NULL terminator, frame argv matches sameconstant, noargs c020 rejected, stderr/raw41 preserved, streams1024, original10s/TERM/KILL/reap/5s deadlines/retirement errors unchanged. No F05 gate fixture runtime.'}],
 'composition_binding_fix':{'required_sidecar':'Source-bound collector caseprofile record declaring exactargv/env/cwd/reportlimits/timeouts and compiled artifact hash, sourceclosure and actualHOSTqualification. This catches original defect before native.','manifest_and_overlay':'Fresh separate Ruststartupcollector hash instaging.collector and overlay.finalmap init/source, derivedcpio/hash, exactmanifest/sourcepublication/outerbindings coherent. Currente5d executor, payloadff227, fixedloader/libc/libnuma and originalstartuporacle unchanged.','evaluator':'Keep5298 fullruntimeevaluator argv comparison/oracle unchanged. Newsourcecasebinding supplements metadata; no pass from plan alone.'},
 'next_executable_check':'Root assigns separate Ruststartup source successor to F05 Rustowner; after exactdelta independent review and ordinary compile grant, run actualHOST fakeexec harness verifying eight argv elements including zero-length element and finalNULL, plus exactND_PAYLOAD startupframe. No native retry before this passes and currentbe6e owner independently retires.',
 'not_claimed':['No startupnativePASS','No executorbug or correctargv execution proof','No currentpaired Cbaselinecomparison','No all349/all51/allocation/file retirement','No newsourceinventory orCcompile'],
 'references':refs,'pure_readonly_checks':checks,'operations':{'compiler':0,'test_executable':0,'Docker':0,'guest':0,'resource_or_account_or_guard_queries':0,'cleanup':0,'canonical_Git':0,'subagents':0},
 'constraints':{'fixed_UTC':'2026-10-28T05:36:09Z','MONO':947874.5689514667,'BOOT':963213.6960030915,'credit_run':'7f4af94a83b14cc08f97401f5891d965','credit_ceiling':57774.852125,'prior_spent_floor':22812.3311,'all_holds_oneheavy_and_parent_exclusive_controls':True}}
for name,obj in [('PROPOSAL.json',proposal),('PURE-SOURCE-CHECKS.json',{'status':'PASS_READONLY_RETAINED_SOURCE_CAUSAL_CHECKS','checks':checks,'executed_workload':False})]:
 p=OUT/name
 with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
ready={'scope':proposal['scope'],'status':proposal['status'],'proposal':{'path':str(OUT/'PROPOSAL.json'),'sha256':hashlib.sha256((OUT/'PROPOSAL.json').read_bytes()).hexdigest()},'checks':len(checks),'source_refs':len(refs),'extractor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runtime_authority':None}
with (OUT/'READY.json').open('x') as f:json.dump(ready,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(ready));print('READY_SHA256',hashlib.sha256((OUT/'READY.json').read_bytes()).hexdigest())
