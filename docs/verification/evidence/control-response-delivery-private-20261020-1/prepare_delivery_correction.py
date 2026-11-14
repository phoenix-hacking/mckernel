from pathlib import Path
import json,hashlib,difflib,sys
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;S=P/'source/host-kernel/native-rust'
s=(P/'actual-control-delivery.rs').read_text();original=s
app=(S/'smp_application.rs').read_text()
helpers=[balanced_item(app,n)for n in ['fn fork_ack_publication_frozen(','fn publish_fork_ack_in_slots(']]
marker=next(l for l in app.splitlines()if l.startswith('const FORK_CARRIER_MARKER:'))
assert marker=='const FORK_CARRIER_MARKER: u64 = 0x313030434b46434d;'
assert 'FORK_CARRIER_MARKER'not in s
needle='fn fork_publication_frozen('
assert s.count(needle)==1;s=s.replace(needle,marker+'\n'+'\n'.join(helpers)+'\n'+needle,1)
old=(P.parent/'control-receipt-1/actual-control-receipt-corrected.rs').read_text()
accessor=balanced_item(old,'pub(crate) fn fixture_response_identity_held(')
module=balanced_item(s,'mod smp_application_syscall{')
assert 'fixture_response_identity_held'not in module
extended=module[:-1]+'\n#[cfg(test)] impl<M:ResponseMemory> Mailbox<M>{\n'+accessor+'\n}\n}'
assert s.count(module)==1;s=s.replace(module,extended,1)
for n,h in zip(['fn fork_ack_publication_frozen(','fn publish_fork_ack_in_slots('],helpers):assert balanced_item(s,n)==h
assert balanced_item(s,'pub(crate) fn fixture_response_identity_held(')==accessor
assert (S/'smp_application_syscall.rs').read_text()in balanced_item(s,'mod smp_application_syscall{')
target=P/'actual-control-delivery-corrected.rs';assert not target.exists();target.write_text(s)
(P/'delivery-fixture-correction.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='actual-control-delivery.rs',tofile=target.name)))
body=json.loads((P/'actual-body-bindings.json').read_text())
for n,h in zip(['fn fork_ack_publication_frozen(','fn publish_fork_ack_in_slots('],helpers):body['rows'].append({'source':'smp_application.rs','item':n,'sha256':hashlib.sha256(h.encode()).hexdigest(),'exact':True,'execution_claim':'compile dependency only, not ACK acceptance'})
body['actual_ACK_marker_const']={'text':marker,'sha256':hashlib.sha256(marker.encode()).hexdigest(),'exact':True}
body['test_only_accessor_restored']={'source':str(P.parent/'control-receipt-1/actual-control-receipt-corrected.rs'),'sha256':hashlib.sha256(accessor.encode()).hexdigest(),'readonly':True}
(P/'actual-body-bindings-corrected.json').write_text(json.dumps(body,indent=2)+'\n')
runner=(P/'run_delivery_check.py').read_text().replace("E=R/'check-1'","E=R/'check-2'").replace("R/'fixture-inputs.json'","R/'fixture-correction-inputs.json'")
runner=runner.replace(str(P/'actual-control-delivery.rs'),str(target)).replace(str(P/'check-1/actual'),str(P/'check-2/actual'))
assert not(P/'run_delivery_check_correction.py').exists();(P/'run_delivery_check_correction.py').write_text(runner)
inputs=json.loads((P/'fixture-inputs.json').read_text())['inputs']
for f in [Path(__file__),target,P/'run_delivery_check_correction.py',P/'delivery-fixture-correction.patch',P/'actual-body-bindings-corrected.json',P/'check-1/compile.status.json',P/'check-1/compile.stderr',P/'whole-check.status.json']:
 inputs.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'fixture-correction-inputs.json').write_text(json.dumps({'inputs':inputs,'new_scenarios':4,'source_unchanged':True,'isolation':'one exact test process per Joined arena','first_compile_preserved':True,'old_tests_executed':False},indent=2)+'\n')
proposal=json.loads((P/'delivery-check-command.json').read_text());proposal['status']='READY_NOT_RUN_FIXTURE_CORRECTION';proposal['runner']=str(P/'run_delivery_check_correction.py');proposal['fixture_inputs']=str(P/'fixture-correction-inputs.json');proposal['output_root']=str(P/'check-2');proposal['argv'][-1]=proposal['runner']
for _,argv in proposal['commands']:
 for i,a in enumerate(argv):
  if a==str(P/'actual-control-delivery.rs'):argv[i]=str(target)
  if a==str(P/'check-1/actual'):argv[i]=str(P/'check-2/actual')
proposal['fixture_correction']='exact two ACK helpers + exact actual marker constant; restore prior readonly Mailbox identity view; no production/scenario change'
(P/'delivery-fixture-correction-command.json').write_text(json.dumps(proposal,indent=2)+'\n')
assert hashlib.sha256((P/'control-response-delivery.patch').read_bytes()).hexdigest()=='f5b8c603448a10fbdc02eab58bd95b966026272914e3e81cf8174d419a106d79'
print('proposal',hashlib.sha256((P/'delivery-fixture-correction-command.json').read_bytes()).hexdigest(),'actual_body_bindings',len(body['rows']),'commands',len(proposal['commands']))
