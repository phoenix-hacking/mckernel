# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,re,shutil,os
P=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/next-live-observation-221b-1/service-ebusy-diagnostic-1');scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
b=json.loads((P/'SOURCE-BINDINGS.json').read_text());r=json.loads((P/'ACTUAL-FIXTURE-RECEIPT.CORRECTION-1.json').read_text());assert len(b['changes'])==7
for v in b['changes'].values():
 for kind in ['selected_original','private_postimage']:assert pin(Path(v[kind]['path']))==v[kind]
 observed=pin(Path(v['canonical_preimage']['path']));assert observed['sha256'] in [v['canonical_preimage']['sha256'],v['private_postimage']['sha256']]
# Source-bound formatting witnesses for every new fixed format. Use x86_64
# maximum widths, actual 16-ticket bound, signed errno/IDs and Option widths.
U32='4294967295';U64='18446744073709551615';I32='-2147483648';I64='-9223372036854775808';HX='ffffffffffffffff';OPT='Some('+U64+')';prefix=96
rows=[]
for key in b['changes']:
 s=(P/'source'/key).read_text()
 for match in re.finditer(r'pr_err!\("(IHK-[A-Z] [^"\n]*)"',s):
  fmt=match.group(1).replace('\\n','\n');fields=re.findall(r'\{[^}]*\}',fmt);values=[]
  # Fixed per-field label defines the source type (actual types compiled in
  # extracted helpers except procfs's same original single AtomicI32 load).
  for f in re.finditer(r'([a-z_]+)=\{([^}]*)\}',fmt):
   label,spec=f.groups()
   if label=='os':value=U32
   elif label=='g':value=U64
   elif label=='d':value='16'
   elif label=='at':value='prepare_cleanup' if fmt.startswith('IHK-A') else 'publish_syscalls'
   elif spec==':x':value=HX
   elif spec==':?':
    value={'k':'ExecPayload','j':OPT,'s':OPT,'ret':'Some('+I32+')','seal':'Some(false)','ph':'Published'}.get(label,OPT)
   elif label in ['node','prep','rev','inh','need','sch','q','closed','drain','res']:value='1'
   elif label in ['ch','i']:value=U64
   elif label in ['s']:value=U64
   elif label=='c' and 'ch=' in fmt:value=U32
   elif label in ['e','p','c','rq','to','port','busy','op_e','peer_e','v']:value=I32
   elif label=='value':value=I64
   else:raise AssertionError((key,fmt,label,spec))
   values.append(value)
  assert len(fields)==len(values),(fmt,fields,values)
  it=iter(values);line=re.sub(r'\{[^}]*\}',lambda _:next(it),fmt);total=len(line.encode())+prefix;assert total<=255,(key,fmt,total)
  rows.append(dict(source_key=key,line=s[:match.start()].count('\n')+1,actual_format=fmt,worst_width_body=line,body_bytes=len(line),prefix_budget_bytes=prefix,total_bytes=total))
assert rows
write(P/'DIAGNOSTIC-LINE-WIDTH-SOURCE-WITNESS.json',dict(scope=scope,status='PASS_ALL_NEW_FIXED_FORMATS_SOURCE_BOUND',formats=len(rows),source_binding=pin(P/'SOURCE-BINDINGS.json'),maximum_total_bytes=max(x['total_bytes'] for x in rows),parser_limit_bytes=255,models='Width-only synthetic extrema are not runtime packet identities. 96-byte conservative printk/module/time prefix budget. Pure actual Rust formatting assertions also ran for extracted helpers; procfs IHK-W and maximal remote token values have this static bound.',rows=rows))
for rec in r['records']:
 j=rec['join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None
 assert not Path('/proc/'+str(j['pid'])).exists(),j['pid']
write(P/'ACTUAL-WHOLE-JOIN.json',dict(scope=scope,status='PASS_CORRECTED_PURE_FIXTURE_WHOLE_JOIN',fixture_receipt=pin(P/'ACTUAL-FIXTURE-RECEIPT.CORRECTION-1.json'),whole_parent_tool_returncode=0,all_direct_children_joined=True,all_groups_absent=True,all_streams_closed=True,all_errors_null=True,CPU0_released=True,commands=r['records'],failure_history=r['failure_history'],prior_failure_preserved=pin(P/'FAILURE-1.json'),source_binding=pin(P/'SOURCE-BINDINGS.json'),diagnostic_only_not_semantic_repair=True,actual_faulting_packet_unknown=True))
positions={}
markers={'smp_service.rs':['enum FailureOrigin','fn diagnostic_ticket','fn failure_context','self.fail(error, FailureOrigin::Packet','self.fail(error, FailureOrigin::ControlPump'], 'sysfs_memory.rs':['fn diagnostic_conflict(','pub(super) fn procfs(','fn diagnostic_conflict_failure(','fn diagnostic_completion_failure(','pub(super) fn syscall(','wire::complete_observed'], 'sysfs_zeroing.rs':['"zero_control"','"zero_header"','"zero_chunk"','"zeroed_head"'], 'sysfs_remote.rs':['pub(crate) fn reply('], 'sysfs_rpc.rs':['pub(crate) fn reply_failure_context('], 'abi/sysfs_request.rs':['pub(crate) struct CompletionBusy','pub(crate) unsafe fn complete_observed('], 'smp_application.rs':['fn diagnostic_application_failure(','"procfs_backend"','"prepare_cleanup"']}
for k,ms in markers.items():
 s=(P/'source'/k).read_text();positions[k]={m:s[:s.index(m)].count('\n')+1 for m in ms}
ready=dict(scope=scope,status='READY_FOR_INDEPENDENT_SOURCE_REVIEW_AND_SDK7_SOURCE_PREPARATION_ONLY',source_binding=pin(P/'SOURCE-BINDINGS.json'),patch=pin(P/'PRIVATE-DIAGNOSTIC.patch'),actual_fixture=pin(P/'ACTUAL-FIXTURE-RECEIPT.CORRECTION-1.json'),whole_join=pin(P/'ACTUAL-WHOLE-JOIN.json'),line_width_witness=pin(P/'DIAGNOSTIC-LINE-WIDTH-SOURCE-WITNESS.json'),positions=positions,changed_keys=list(b['changes']),sourcepostimages={k:v['private_postimage'] for k,v in b['changes'].items()},qualification=['Actual round48 EBUSY cause and faulting packet remain unknown. Adjacent valid delivery rows are not attributed.','Memory::claim EBUSY swallowed branch unchanged; syscall response claim is distinct.','Original predicates/errors/tag release/quarantine/ACK/deadline/order remain unchanged; diagnostic counters are separate bounded16 each.','ABI complete observes its original single busy load only while caller retains claim and ledger mutex; original Claim.finish removal/active=false sequencing unchanged.','Remote token uses actual initialized bytes24..32, not app token16..24. No packet padding dump.','Application snapshots cover only two authorized error returns under existing slots lock; actual Entry backend_ready/request_cleanup bodies unchanged.','Pure fixture models kernel Arc/Mutex/Vec, mapping, application receiver/state and notifier primitives. It is not full SDK7 source compile, module ABI, native runtime or semantic repair proof.','Original one missingconstant compile failure retained; sole bounded correction passed. No further fixture attempts authorized by this receipt.'],next_operation='Independent seven-source ABI/ownership/diagnostic-only review, then root-authorized coherent existing68source SDK7 staging/build under separate release; root owns canonical integration/runtime.',SDK7_module_compile=None,native_diagnostic_run=None,semantic_repair=None,CPU0_released=True,worker_canonical_mutations=0,canonical_state_at_fixture_receipt='PREIMAGES_UNCHANGED',canonical_state_now='ALL_SEVEN_MATCH_PRIVATE_POSTIMAGES_ROOT_OWNED_INTEGRATION_OBSERVED',canonical_observation={k:pin(Path(v['canonical_preimage']['path'])) for k,v in b['changes'].items()})
write(P/'READY-FOR-REVIEW.json',ready)
E.mkdir(parents=True,exist_ok=True)
# Durable binary remains at its bound private path; mirror all source, captures,
# generator, failure and result evidence without duplicating executable bytes.
mirrored=[]
for q in sorted(P.rglob('*')):
 if not q.is_file() or any(x.startswith('fixture-output-') for x in q.relative_to(P).parts):continue
 dest=E/q.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copy2(q,dest);assert q.read_bytes()==dest.read_bytes();mirrored.append(str(q.relative_to(P)))
record=dict(scope=scope,status='PASS_BYTE_EXACT_SOURCE_CAPTURE_RECEIPT_MIRROR',private_root=str(P),evidence_root=str(E),files=len(mirrored),relative_paths=mirrored,private_ready=pin(P/'READY-FOR-REVIEW.json'),evidence_ready=pin(E/'READY-FOR-REVIEW.json'),durable_binary_not_duplicated=json.loads((P/'DURABLE-FIXTURE-BINARY.CORRECTION-1.json').read_text())['binary'],CPU0_released=True)
write(P/'MIRROR-RECEIPT.json',record);write(E/'MIRROR-RECEIPT.json',record)
print(json.dumps(dict(ready=pin(P/'READY-FOR-REVIEW.json'),whole_join=pin(P/'ACTUAL-WHOLE-JOIN.json'),mirror=pin(P/'MIRROR-RECEIPT.json'),max_line_plus96=max(x['total_bytes'] for x in rows),files=len(mirrored))))
