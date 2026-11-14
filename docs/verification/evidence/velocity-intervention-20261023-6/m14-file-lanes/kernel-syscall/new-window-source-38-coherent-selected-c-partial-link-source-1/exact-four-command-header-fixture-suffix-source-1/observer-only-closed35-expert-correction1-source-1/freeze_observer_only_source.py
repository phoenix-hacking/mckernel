"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static exact object/source proof materialization and observer-only source preparation.
"""
from pathlib import Path
import ast,copy,hashlib,json,re,struct
B=Path(__file__).resolve().parent;P=B.parent
F=json.loads((P/'STATIC-SYSCALL-CLOSED35-SOURCE-AND-OUTGOING-RELA.FACTS.json').read_text());UTIL=json.loads((P/'STATIC-UTIL-THREAD-EXACT-SIX-LINE-IMMEDIATES.FACTS.json').read_text())
r=json.loads((P/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json').read_text());m=json.loads(Path(r['input_map']['path']).read_text());spec=json.loads((P/'EXACT-SOURCE38-FOUR-COMMAND-ENVELOPE.SOURCE-ONLY.json').read_text())
def pin(p):
 p=Path(p);v=p.read_bytes();return dict(path=str(p),bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
def save(name,value):
 with (B/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
 return pin(B/name)
def need(c,msg):
 if not c:raise ValueError(msg)
ns=dict(Path=Path,struct=struct);nodes=[n for n in ast.parse(Path(m['qualified_Elf_source']['path']).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Elf' or isinstance(n,ast.FunctionDef) and n.name in {'object_bytes','owning_relocations'}];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<static ELF reader>','exec'),ns)
Elf=ns['Elf'];old=Elf(Path(F['old_syscall']['path']));new=Elf(Path(F['actual_syscall']['path']));partial=Elf(Path(F['actual_partial']['path']))
inputs=[pin(p) for p in r['commands'][2]['argv'][4:]];assert len(inputs)==5
proof=[]
for p in inputs+[F['actual_partial']]:
 e=Elf(Path(p['path']));assert not set(F['D_removed']) & {s['name'] for s in e.symbols}
 count=0
 for sec in e.sections:
  if sec['type']!=4 or not e.sections[sec['info']]['flags']&2:continue
  for i in range(sec['size']//24):
   off,info,add=struct.unpack_from('<QQq',e.raw,sec['offset']+24*i);assert e.symbols[info>>32]['name'] not in F['D_removed'];count+=1
 proof.append(dict(input=p,ALLOC_RELA_count=count))
uowners=[]
for sec in old.sections:
 if sec['type']!=4:continue
 for i in range(sec['size']//24):
  off,info,add=struct.unpack_from('<QQq',old.raw,sec['offset']+24*i);target=old.symbols[info>>32]
  if target['name'] not in F['U_removed']:continue
  owners=[f for f in F['closed35_objects'] if f['outgoing_RELA'] and f['symbol']['shndx']==sec['info'] and f['symbol']['value']<=off<f['symbol']['value']+f['symbol']['size']]
  assert len(owners)==1
  uowners.append(dict(name=target['name'],fixture=owners[0]['name'],offset=off,type=info&0xffffffff,addend=add))
source=Path(F['old_source']['path']).read_text().splitlines(keepends=True)
helper={};exec(compile((B/'validate_exact_syscall_fixture_contract.py').read_bytes(),'<exact static semantic source helper>','exec'),helper)
semantic=helper['util_semantic_relocations'](old,new,F['old_source'],F['current_source'],ns['object_bytes'],ns['owning_relocations'],need)
actual=P/'fixed-reviewed-environment-admission-1';origin=[Path(F['old_source']['path']),Path(F['current_source']['path']),Path(F['actual_old_producer']['path']),Path(F['actual_old_join']['path']),actual/'ACTUAL-SOURCE38-FOUR-COMMAND-FIRST-RESULT.json',actual/'actual-four-command-capture-1/03/stderr',actual/'actual-four-command-capture-1/01/whole-join-and-end.json',actual/'actual-four-command-capture-1/02/whole-join-and-end.json',P/'STATIC-SYSCALL-CLOSED35-SOURCE-AND-OUTGOING-RELA.FACTS.json',P/'STATIC-UTIL-THREAD-EXACT-SIX-LINE-IMMEDIATES.FACTS.json']
auth={p['path']:p for p in inputs+[F['old_syscall'],F['actual_syscall'],F['actual_partial']]+[pin(p) for p in origin]}
contract=copy.deepcopy(F);contract.update(status='SOURCE_ONLY_EXPERT_EXACT_CLOSED35_D_CLOSED21_U_ROLE_CONTRACT',complete_source_append=dict(first_line=29324,last_line=len(source),exact_text=''.join(source[29323:]),sha256=hashlib.sha256(''.join(source[29323:]).encode()).hexdigest()),five_actual_partial_inputs=inputs,actual_input_consumer_proofs=proof,exact_removed_U_relocation_owners=sorted(uowners,key=lambda x:x['name']),strict_partial_U19=m['strict_expected_remaining_C_imports'],authenticated_inputs=list(auth.values()),util_exact_line_immediates=UTIL,util_semantic_relocations=semantic,expert_scope='Exact35 fixture definitions and exact21 imports exclusively owned by22fixture pointers; distinct process20 gate unchanged. No runtime import/code waiver.',execution=False)
cpin=save('EXACT-SYSCALL-CLOSED35-CLOSED21-OWNED22-CONTRACT.json',contract)
obs=(P/'observe_selected_coherent_partial.NOT-RUN.py').read_text();obs=obs.replace("out = ROOT / 'output-1'", "out = Path(recipe['retained_output_root'])")
obs=obs.replace("for path in recipe['commands'][2]['argv'][4:]:", "for path in recipe['retained_partial_inputs']:")
insert="""syscall_contract = json.loads(auth(recipe['syscall_closed35_contract']))
closed35_ns = {}
exec(compile(auth(recipe['syscall_closed35_validator']), recipe['syscall_closed35_validator']['path'], 'exec'), closed35_ns)
closed35_D, closed21_U, syscall_fixture_proof = closed35_ns['validate'](syscall_contract,Elf,object_bytes,owning,auth,need)
"""
obs=obs.replace("for name, elf in [('process',process),('syscall',syscall)]:",insert+"for name, elf in [('process',process),('syscall',syscall)]:",1)
obs=obs.replace("    need(defined(elf) == expected_D,", "    if name == 'syscall':\n        expected_D -= closed35_D\n    need(defined(elf) == expected_D,",1)
obs=obs.replace("    need(undefined(elf) == set(m['old_' + name + '_U']), 'selected C imports changed outside declaration selectors: ' + name)","    expected_U = set(m['old_' + name + '_U'])\n    if name == 'syscall':\n        expected_U -= closed21_U\n    need(undefined(elf) == expected_U, 'selected C imports changed outside exact fixture role selectors: ' + name)")
obs=obs.replace("result = dict(closed20_fixture_role=", "result = dict(syscall_closed35_fixture_role=recipe['syscall_closed35_contract'],syscall_closed35_proof=syscall_fixture_proof,closed20_fixture_role=")
(B/'observe_selected_coherent_partial.NOT-RUN.py').write_text(obs)
original_commands=r['commands'];r['commands']=[copy.deepcopy(original_commands[3])];r['commands'][0]['argv'][-1]=str(B/'observe_selected_coherent_partial.NOT-RUN.py');r['commands'][0]['cwd']=str(B);r['commands'][0]['purpose']='Functional McKernel OS/apps and Rust/assembly migration only; no security testing. ONE observer-only closed35/21/22 fixture-role correction on exact retained process/syscall/partial; all ABI/provider/storage/import/machine checks preserved, no compiler/link replay.'
r.update(status='SOURCE_ONLY_ONE_OBSERVER_EXPERT_CORRECTION_NOT_GRANTED',syscall_closed35_contract=cpin,syscall_closed35_validator=pin(B/'validate_exact_syscall_fixture_contract.py'),retained_output_root=str(P/'output-1'),retained_partial_inputs=[p['path'] for p in inputs],fresh_output_root=str(B/'output-1'),changed_C_compiler_jobs=0,syntax_only_jobs=0,root_grant=None,predecessor_recipe=pin(P/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json'))
pins={p['path']:p for p in r['pinned_inputs'] if p['path']!=str(P/'observe_selected_coherent_partial.NOT-RUN.py')};pins.update(auth)
for p in [B/'observe_selected_coherent_partial.NOT-RUN.py',B/'validate_exact_syscall_fixture_contract.py',B/'EXACT-SYSCALL-CLOSED35-CLOSED21-OWNED22-CONTRACT.json',P/'output-1/syscall.selected.d']:
 pins[str(p)]=pin(p)
r['pinned_inputs']=list(pins.values());recipe=save('EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json',r)
ready=save('READY-SOURCE38-ONE-OBSERVER.NOT-GRANTED.json',dict(scope=r['scope'],status='SOURCE_ONLY_NO_EXECUTION_NOT_GRANTED',recipe=recipe,closed35_contract=cpin,commands=r['commands'],compiler_replay=0,link_replay=0,actual_observer=False))
manifest=save('FINITE-SOURCE38-ONE-OBSERVER.FILES.json',dict(scope=r['scope'],files=[pin(B/name) for name in ['freeze_observer_only_source.py','validate_exact_syscall_fixture_contract.py','observe_selected_coherent_partial.NOT-RUN.py','EXACT-SYSCALL-CLOSED35-CLOSED21-OWNED22-CONTRACT.json','EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json','READY-SOURCE38-ONE-OBSERVER.NOT-GRANTED.json']]))
headers={p['path'] for p in spec['batched_header_inputs']};spec.update(recipe=recipe,source_READY=ready,source_manifest=manifest,execution=False,actual_PID=None,actual_root_grant=None,critical_recipe_inputs=[p for k,p in pins.items() if k not in headers]);spec['critical_recipe_count']=len(spec['critical_recipe_inputs'])
assert spec['critical_recipe_count']+9<=64,spec['critical_recipe_count']
specpin=save('EXACT-SOURCE38-ONE-OBSERVER-ENVELOPE.SOURCE-ONLY.json',spec)
runner=(actual/'run_source38_four_commands_once.NOT-GRANTED.py').read_text();runner=re.sub(r'^SPEC = .*$', 'SPEC = '+repr(specpin),runner,flags=re.M);runner=re.sub(r'^RECIPE = .*$', 'RECIPE = '+repr(recipe),runner,flags=re.M)
runner=runner.replace('FOUR-COMMAND','ONE-OBSERVER').replace('four-command','one-observer').replace('four positive','one positive').replace("len(recipe['commands'])==4","len(recipe['commands'])==1").replace('FOUR_COMMAND','ONE_OBSERVER')
runner=runner.replace("outputs = [byte_pin(output/name) for name in ('syscall.selected.o','syscall.selected.d','coherent-selected.partial.o')]", "outputs = [byte_pin(Path(recipe['retained_output_root'])/name) for name in ('syscall.selected.o','syscall.selected.d','coherent-selected.partial.o')]\n        outputs += [byte_pin(recipe['retained_process']['path']),byte_pin(recipe['retained_process_dependencies']['path'])]")
(B/'run_source38_one_observer_once.NOT-GRANTED.py').write_text(runner)
for name in ['run_source38_one_observer_once.NOT-GRANTED.py','observe_selected_coherent_partial.NOT-RUN.py','validate_exact_syscall_fixture_contract.py']:ast.parse((B/name).read_text())
final=save('FROZEN-SOURCE38-ONE-OBSERVER-READY.NOT-GRANTED.json',dict(scope=r['scope'],status='SOURCE_ONLY_READY_FOR_INDEPENDENT_REVIEW_AND_ROOT_GRANT',recipe=recipe,spec=specpin,runner=pin(B/'run_source38_one_observer_once.NOT-GRANTED.py'),closed35_contract=cpin,source_READY=ready,source_manifest=manifest,observer=pin(B/'observe_selected_coherent_partial.NOT-RUN.py'),validator=pin(B/'validate_exact_syscall_fixture_contract.py'),exact_command=['env','MCKERNEL_OS_MEMORY_GIB=22.0485','taskset','-c','7','/home/holden/anaconda3/bin/python3','-I','-B',str(B/'run_source38_one_observer_once.NOT-GRANTED.py')],execution=False,actual_observer_run=False,critical_recipe_inputs=spec['critical_recipe_count'],headers=len(headers),FD_limit=256,compiler_or_link_replays=0))
print(json.dumps(dict(READY=final,recipe=recipe,spec=specpin,runner=pin(B/'run_source38_one_observer_once.NOT-GRANTED.py'),critical=spec['critical_recipe_count']),indent=2))
