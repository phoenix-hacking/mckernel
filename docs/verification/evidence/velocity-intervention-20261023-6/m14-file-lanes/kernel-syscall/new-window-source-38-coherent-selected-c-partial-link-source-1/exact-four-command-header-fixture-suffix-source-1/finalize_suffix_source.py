"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finalize additive source bindings only; no compiler/test/query/workload execution.
"""
import ast,hashlib,json,re
from pathlib import Path
B=Path(__file__).resolve().parent
A=B.parent.parent.parent/'x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1'
def pin(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(n):return json.loads((B/n).read_text())
def save(n,d):
 (B/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');return pin(B/n)
f=load('EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json')
original=pin(A/'output-1/process.selected.o');assert original['sha256']==f['old_process']['sha256'] and original['bytes']==f['old_process']['bytes']
command=json.loads((A/'actual-current285-data5-attempt-1/00/command.json').read_text());joined=json.loads((A/'actual-current285-data5-attempt-1/00/WHOLE-JOIN.json').read_text())
assert command['argv'][command['argv'].index('-c')+1]==str(A/'source/kernel/process.c')
assert command['argv'][command['argv'].index('-o')+1]==original['path']
assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error'] and not joined['timed_out']
f['source17_exact_output']=original;f['source17_output_is_byte_identical_to_reused_old_process']=True;f['source17_actual_compile_join']=joined
contract=save('EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json',f)
p=B/'freeze_suffix_source.py';t=p.read_text();t=re.sub(r"source=A/'source/kernel/process.c';assert .*? if False else True", "source=A/'source/kernel/process.c'",t);p.write_text(t)
r=load('EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json');r['closed20_fixture_contract']=contract
pins={row['path']:row for row in r['pinned_inputs']};pins[contract['path']]=contract;pins[original['path']]=original
lexical=str(B/'quote-root/kernel/../executer/include/uti.h');pins[lexical]=pin(lexical)
r['pinned_inputs']=list(pins.values());r['quote_namespace']['compiler_dependency_lexical_alias']=pin(lexical)
recipe=save('EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json',r)
ready=load('READY-SOURCE38-FOUR-COMMAND-SUFFIX.NOT-GRANTED.json');ready.update(recipe=recipe,closed20_fixture_contract=contract)
ready=save('READY-SOURCE38-FOUR-COMMAND-SUFFIX.NOT-GRANTED.json',ready)
manifest=save('FINITE-SOURCE38-FOUR-COMMAND-SUFFIX.FILES.json',dict(scope=r['scope'],files=[pin(B/n) for n in ['freeze_suffix_source.py','finalize_suffix_source.py','observe_selected_coherent_partial.NOT-RUN.py','EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json','quote-root/executer/include/uti.h','EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json','READY-SOURCE38-FOUR-COMMAND-SUFFIX.NOT-GRANTED.json']]))
s=load('EXACT-SOURCE38-FOUR-COMMAND-ENVELOPE.SOURCE-ONLY.json');s.update(recipe=recipe,source_READY=ready,source_manifest=manifest,closed20_fixture_contract=contract)
headers={row['path'] for row in s['batched_header_inputs']};s['critical_recipe_inputs']=[v for k,v in pins.items() if k not in headers];s['critical_recipe_count']=len(s['critical_recipe_inputs'])
assert s['critical_recipe_count']<50
spec=save('EXACT-SOURCE38-FOUR-COMMAND-ENVELOPE.SOURCE-ONLY.json',s)
p=B/'run_source38_four_commands_once.NOT-GRANTED.py';t=p.read_text();t=re.sub(r'^SPEC = .*$', 'SPEC = '+repr(spec),t,flags=re.M);t=re.sub(r'^RECIPE = .*$', 'RECIPE = '+repr(recipe),t,flags=re.M);p.write_text(t)
# Static syntax parse only. Do not execute the prepared observer or runner.
for p in [B/'observe_selected_coherent_partial.NOT-RUN.py',B/'run_source38_four_commands_once.NOT-GRANTED.py']:ast.parse(p.read_text())
command=['taskset','-c','7','/home/holden/anaconda3/bin/python3','-I','-B',str(p)]
final=save('FROZEN-SOURCE38-FOUR-COMMAND-READY.NOT-GRANTED.json',dict(scope=r['scope'],status='SOURCE_ONLY_READY_FOR_INDEPENDENT_REVIEW_AND_EXACT_ROOT_GRANT',recipe=recipe,spec=spec,runner=pin(p),source_READY=ready,source_manifest=manifest,closed20_fixture_contract=contract,observer=pin(B/'observe_selected_coherent_partial.NOT-RUN.py'),exact_command=command,grant_path=str(B/'ROOT-EXACT-SOURCE38-FOUR-COMMAND-GRANT.json'),execution=False,critical_recipe_inputs=s['critical_recipe_count'],headers=len(headers),FD_limit=256,source_only_AST_parse=True,actual_commands_run=0))
print(json.dumps(dict(final=final,recipe=recipe,spec=spec,runner=pin(p),command=command),indent=2))
