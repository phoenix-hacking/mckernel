from pathlib import Path
import json,hashlib,difflib,sys
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent
s=(P/'actual-control-delivery-corrected.rs').read_text();old=s
a='assert_eq!(request.requester(),202);'
b='assert_eq!(request.requester(),101);assert_eq!(request.target(),202);'
assert s.count(a)==1;s=s.replace(a,b,1)
a='guest_transport_word(16,3);assert_eq!(crate::smp_application::queue_control_actual(&j.remote,j.parent,w,s),Err(-71));'
b='guest_transport_word(16,3);assert_eq!(crate::smp_application::queue_control_actual(&j.remote,j.parent,w,s),Err(-16));'
assert s.count(a)==1;s=s.replace(a,b,1)
target=P/'actual-control-delivery-identity-fixed.rs';assert not target.exists();target.write_text(s)
(P/'delivery-identity-correction.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='actual-control-delivery-corrected.rs',tofile=target.name)))
source=P/'source/host-kernel/native-rust'
body=json.loads((P/'actual-body-bindings-corrected.json').read_text())
for row in body['rows']:
 if row.get('item') and row.get('source'):
  actual=balanced_item((source/row['source']).read_text(),row['item']);assert actual==balanced_item(s,row['item'])
body['identity_oracle_correction']='actual decode:wire48 guestrequester101,wire52 hosttarget202; bytes unchanged'
body['bad_wake_oracle_correction']='actual check_fork_unpublished returnsEBUSY-16 onstate3 before CAS; unchanged production result'
(P/'actual-body-bindings-identity-fixed.json').write_text(json.dumps(body,indent=2)+'\n')
runner=(P/'run_delivery_check_correction.py').read_text().replace("E=R/'check-2'","E=R/'check-3'").replace("R/'fixture-correction-inputs.json'","R/'fixture-identity-inputs.json'")
runner=runner.replace(str(P/'actual-control-delivery-corrected.rs'),str(target)).replace(str(P/'check-2/actual'),str(P/'check-3/actual'))
(P/'run_delivery_check_identity_fixed.py').write_text(runner)
inputs=json.loads((P/'fixture-correction-inputs.json').read_text())['inputs']
for f in [Path(__file__),target,P/'run_delivery_check_identity_fixed.py',P/'delivery-identity-correction.patch',P/'actual-body-bindings-identity-fixed.json',P/'check-2/scenario-1.status.json',P/'check-2/scenario-1.stderr',P/'whole-check-correction.status.json']:
 inputs.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'fixture-identity-inputs.json').write_text(json.dumps({'inputs':inputs,'source_unchanged':True,'scenarios':4,'wire_bytes_unchanged':True,'prior_both_failures_preserved':True,'isolation':'one exact process per once-only guest arena'},indent=2)+'\n')
proposal=json.loads((P/'delivery-fixture-correction-command.json').read_text());proposal['status']='READY_NOT_RUN_EXPERT_CLASSIFIED_CORRECTION';proposal['runner']=str(P/'run_delivery_check_identity_fixed.py');proposal['fixture_inputs']=str(P/'fixture-identity-inputs.json');proposal['output_root']=str(P/'check-3');proposal['argv'][-1]=proposal['runner']
for _,argv in proposal['commands']:
 for i,a in enumerate(argv):
  if a==str(P/'actual-control-delivery-corrected.rs'):argv[i]=str(target)
  if a==str(P/'check-2/actual'):argv[i]=str(P/'check-3/actual')
proposal['expert_correction']='two source-derived fixture oracles only: requester101+target202; state3 EBUSY-16 not laterCAS EPROTO-71; actualwire/production/all4vectors unchanged'
(P/'delivery-identity-correction-command.json').write_text(json.dumps(proposal,indent=2)+'\n')
assert hashlib.sha256((P/'control-response-delivery.patch').read_bytes()).hexdigest()=='f5b8c603448a10fbdc02eab58bd95b966026272914e3e81cf8174d419a106d79'
print('proposal',hashlib.sha256((P/'delivery-identity-correction-command.json').read_bytes()).hexdigest(),'commands',len(proposal['commands']),'actual_items',len(body['rows']))
