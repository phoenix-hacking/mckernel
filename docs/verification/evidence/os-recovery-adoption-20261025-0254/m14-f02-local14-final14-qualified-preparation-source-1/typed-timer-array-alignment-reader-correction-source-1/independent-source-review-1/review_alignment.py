"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact existing typed array alignment source delta; no qualifier main or workload.
"""
from pathlib import Path
import ast,datetime,hashlib,json
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent;OLD=P/'absolute-retained-reference-correction-source-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
r=read(Q/'SOURCE-READY.json');p=read(Q/'PROFILE.NOT-GRANTED.json');op=read(OLD/'PROFILE.NOT-GRANTED.json');diag=read(Q/'EXACT-TYPED-ALIGNMENT-DIAGNOSIS.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='959f1129e310b5a0ff9e7efbd9558a97caa068334b353ea54b888912f9ea53c2'
for key in ['profile','diagnosis','command','previous_packet_preserved','retained_identity_manifest']:assert ref(r[key]['path'])==r[key]
prior=OLD/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json';assert ref(prior)['sha256']=='dcff4991ec4067219e6f13367c4e1e10a4bd760a6d70a4f48be26b0f08f0fab8'
for key in ['defining_and_consuming_source','CInt_source','original_C_source','actual168_C_ABI_witness','original_failed_profile','original_results','original_stderr']:assert ref(diag[key]['path'])==diag[key]
ph=Path(diag['defining_and_consuming_source']['path']).read_text();abi=Path(diag['CInt_source']['path']).read_text();c=Path(diag['original_C_source']['path']).read_text()
assert 'pub type CInt = i32;' in abi and 'static process_sched_timer_configuration: [CInt; 2];' in ph and 'pub(super) static process_sched_timer_configuration: [CInt; 2] = [0, 0];' in ph
assert 'const _: [(); 4] = [(); size_of::<CInt>()];' in ph and 'const _: [(); 4] = [(); align_of::<CInt>()];' in ph
assert 'const int process_sched_timer_configuration[2] = { 0, 0 };' in c
oldsrc=(OLD/'qualify_changed_objects.py').read_text();newsrc=(Q/'qualify_changed_objects.py').read_text()
before=" assert z['flags']&2 and not z['flags']&4 and z['align']>=min(size,8) and symbol['value']%min(size,8)==0"
after=""" alignment=min(size,8)
 # Genuine immutable [CInt;2] is size8/align4, not an eight-byte scalar.
 # CInt=i32; defining/consuming type and existing CInt ABI witness are retained.
 if readonly and name=='process_sched_timer_configuration':
  assert size==8
  alignment=4
 assert z['flags']&2 and not z['flags']&4 and z['align']>=alignment and symbol['value']%alignment==0"""
assert oldsrc.count(before)==newsrc.count(after)==1 and newsrc.replace(after,before)==oldsrc
assert 'if readonly:assert not z[\'flags\']&1' in newsrc
rows=diag['retained_metadata'];timer=next(x for x in rows if x['artifact']=='Rust' and x['name']=='process_sched_timer_configuration');assert timer['symbol_size']==8 and timer['section_alignment']==4 and timer['symbol_value']==0 and timer['flags']==0x10000002 and timer['timer_raw_bytes']=='0000000000000000'
stack=next(x for x in rows if x['artifact']=='Rust' and x['name']=='process_init_stack_entry_config');assert stack['symbol_size']==168 and stack['section_alignment']==8
assert len(p['commands'])==1 and p['commands'][0]['argv'][:2]==['/usr/bin/python3','-B'] and p['commands'][0]['argv'][2]==str(Q/'qualify_changed_objects.py') and p['commands'][0]['argv'][3]==op['commands'][0]['argv'][3] and p['commands'][0]['argv'][4]==p['leaves'][0]['output']
for key in ['goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes','scope_limit']:assert p[key]==op[key]
assert not Path(p['capture_root']).exists() and not Path(p['leaves'][0]['output']).exists()
assert all(Path(x['path']).is_absolute() for x in p['inputs'])
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';t=ast.parse(runner.read_text());ns=dict(Path=Path,hashlib=hashlib,json=json,THREAD='01a17e6f-112f-7660-8771-85d15e07a26c',CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','validate_profile'}],type_ignores=[]),'existing pure ordinary profile validator','exec'),ns);ns['validate_profile'](p)
results=read(diag['original_results']['path']);assert len(results['results'])==1
j=results['results'][0]['join'];assert j['returncode']==1 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams']
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_EXACT_NAMED_CINT2_ARRAY_ALIGNMENT_READBACK_CORRECTION',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),reader=ref(Q/'qualify_changed_objects.py'),prior_source_review=ref(prior),diagnosis=ref(Q/'EXACT-TYPED-ALIGNMENT-DIAGNOSIS.json'),retained_identity_manifest=r['retained_identity_manifest'],typed_sources={k:diag[k] for k in ['defining_and_consuming_source','CInt_source','original_C_source','actual168_C_ABI_witness']},exact_timer_diagnostic=timer,exact_initstack168_diagnostic=stack,
findings=['The sole reader source delta replaces the generic min(size,8) alignment check for exactly readonly process_sched_timer_configuration, asserting size8 then requiring alignment4. Reversing this exact seven-line source change reproduces prior reviewed helper bytes; every other source statement/function is identical.',
'Existing defining and consuming type is [CInt;2], with CInt=i32 and existing compiled const size4/align4 witnesses; original C is const int[2]. Size8 does not imply alignment8 for an array. Actual retained diagnostic is size8/value0/section alignment4/ALLOC|LARGE noWRITE and two zero CInt values. The exact-name exception matches this ABI without introducing a mirror or Rust body change.',
'ALLOC, nonEXEC, strict readonly, unique owner, symbol kind/bind/size, raw initializer bytes and relocation rules remain unchanged. readonly=False C fallback path still uses the unchanged original generic rule plus exact17 recorded C storage class. All other names retain original alignment rule, including actual168B initstack size168/align8 and14 Ddebug records with writable flags storage.',
'Actual previous one-qualifier failure1/11.703411s has positive wait/group absence/closed streams and remains preserved; the six producer/CPP/link outputs and41-byte/inode identity manifest remain reused, with no producer or old GLOBAL32 test replay.',
'Exactly one Python qualifier consumes existing artifacts and writes a fresh report/capture. Existing6e98 pure validate_profile passes; resource/fixedclock/account controls are unchanged. Fresh Root CPU6 exclusion/current account/resources/nonce/grant remain required; this source receipt grants no execution.'],
retained_open=['Actual qualifier result and any folded-consumer instruction/dataflow supplement remain pending.','DefaultON unsupported RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR variants, Fugaku exclusion, all-profile object/link/native and whole-file credit remain OPEN.'],blocking_findings=[],source_body_changes=0,reader_alignment_names_changed=1,producer_CPP_link_replays=0,runtime_authority=None,qualifier_main_actions=0,guard_or_resource_queries=0,workloads=0,canonical_mutations=0)
out=D/'INDEPENDENT-SOURCE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),changed_alignment_names=1,blocking_findings=0)))
