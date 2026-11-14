# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,ast
P=Path(__file__).resolve().parent

def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
m=P/'FIXTURE-CORRECTION-1-SOURCE-BINDINGS.json';v=json.loads(m.read_text());v['actual_extracted_bodies']+=['original/actual whole abi/sysfs_request.rs complete including single busy load and final stores','original/actual whole sysfs_rpc.rs accept with typed pending phases and remote token24..32','original/actual sysfs_remote::reply with notification-count comparison','actual application diagnostic helper with explicit host-state model','actual memory diagnostic conflict/completion helpers; all static zeroing context branches'];v['tests']+=' 90original/observed metadata completions,12original/actualRPCpairs,24original/actualRemote.replypairs, application2origin saturation, allnew log body worstwidth checks with96byteprefix.';v['models']+=' Application entry fields and remote lock/data/notifier receiver primitives explicitly modeled. Exact ABI metadata/RPC modules are production source, not modeled layouts.';v['failure_history']=dict(prior_failure=pin(P/'FAILURE-1.json'),cause='Fixture extraction omitted actual REQUEST_MESSAGE constant. No test ran. This is the sole bounded corrected fixture attempt.');m.write_text(json.dumps(v,indent=2)+'\n')
s=(P/'prepare_recipe.py').read_text().replace("F=P/'fixture';O=P/'fixture-output-1'", "F=P/'fixture-correction-1';O=P/'fixture-output-correction-1'")
s=s.replace("P/'FIXTURE-SOURCE-BINDINGS.json'", "P/'FIXTURE-CORRECTION-1-SOURCE-BINDINGS.json'")
s=s.replace("P/'EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json'", "P/'EXACT-ORDINARY-FIXTURE-RECIPE.CORRECTION-1.GRANTED.json'")
s=s.replace("*F.iterdir(),P/'source/smp_service.rs',P/'source/sysfs_memory.rs',P/'PRIVATE-DIAGNOSTIC.patch'", "*F.iterdir(),*(P/'source'/k for k in b['changes']),P/'PRIVATE-DIAGNOSTIC.patch'")
s=s.replace('budgets=16; HOST_PRIMITIVES_MODELED_NO_NATIVE','budgets=16 metadata_pairs=90 rpc_pairs=12 remote_pairs=24 line_prefix_budget=96; HOST_PRIMITIVES_MODELED_NO_NATIVE')
exec(compile(s,str(P/'generated_corrected_recipe.py'),'exec'))
r=P/'EXACT-ORDINARY-FIXTURE-RECIPE.CORRECTION-1.GRANTED.json';v=json.loads(r.read_text());v['failure_history']=json.loads(m.read_text())['failure_history'];v['fixture_scope']=json.loads(m.read_text());r.write_text(json.dumps(v,indent=2)+'\n')
s=(P/'run_fixture_owned.py').read_text().replace('EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json',r.name).replace('fb8fc50b2caf43a68d5fb94a6c7febd36bb420f9cf0b43f9b6008a3b322389e1',pin(r)['sha256'])
for a,z in [('ACTUAL-CAPACITY.json','ACTUAL-CAPACITY.CORRECTION-1.json'),('ACTUAL-PROFILE.json','ACTUAL-PROFILE.CORRECTION-1.json'),('fixture-output-1','fixture-output-correction-1'),('actual-owned-capture-1','actual-owned-capture-correction-1'),('DURABLE-FIXTURE-BINARY.json','DURABLE-FIXTURE-BINARY.CORRECTION-1.json'),('ACTUAL-FIXTURE-RECEIPT.json','ACTUAL-FIXTURE-RECEIPT.CORRECTION-1.json'),('FAILURE-1.json','FAILURE-CORRECTION-1.json')]:s=s.replace(a,z)
s=s.replace('failures=0,corrections=0','failures=1,corrections=1,metadata_completion_pairs=90,RPC_pairs=12,remote_reply_pairs=24,prefix_budget_bytes=96')
s=s.replace("SDK7_module_compile_or_native=None", "SDK7_module_compile_or_native=None,failure_history=recipe['failure_history']")
d=P/'run_fixture_owned_correction_1.py';ast.parse(s);d.write_text(s)
print(json.dumps(dict(corrected_recipe=pin(r),driver=pin(d))))
