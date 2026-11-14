#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source checks; no worker, guard, container or build calls.
"""
import ast,copy,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;E=A.parent
P=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119'
recipe=json.loads((D/'THREE-COMMANDS.SOURCE-ONLY.json').read_text());snapshot=json.loads((D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json').read_text())
for row in snapshot['entries']:
 b=Path(row['source']['path']).read_bytes();assert len(b)==row['source']['bytes'] and hashlib.sha256(b).hexdigest()==row['source']['sha256']
assert len(snapshot['entries'])==149 and len({r['relative'] for r in snapshot['entries']})==149
old=(P/'run_build_only.py').read_text();new=(D/'run_build_only.template.py').read_text()
for name in ('resource_guards','mounts','docker_prefix','docker_argv','current_operation_guard','execute'):
 def segment(text):
  t=ast.parse(text);n=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==name);return ast.dump(n,include_attributes=False)
 if name!='execute':assert segment(old)==segment(new),name
 # execute differs only in fresh container name.
 else:assert segment(old).replace('current119-build-build-only-', 'conversion-first-build-only-')==segment(new)
workerold=(P/'build_only_worker.py').read_text();worker=(D/'build_only_worker.template.py').read_text()
assert worker==workerold.replace("len(plan['commands'])==4,'exact four selected build commands'", "len(plan['commands'])==3,'exact three selected build commands'").replace('ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER','ACTUAL_BUILD_ONLY_THREE_COMMAND_PRODUCER')
mod=ast.parse(new);func=next(x for x in mod.body if isinstance(x,ast.FunctionDef) and x.name=='commands_for_plan')
module=ast.Module(body=[func],type_ignores=[]);ast.fix_missing_locations(module)
def require(ok,msg):
 if not ok:raise ValueError(msg)
ns={'require':require,'read':lambda _:recipe,'auth':lambda _: 'recipe','COMMAND_RECIPE_REF':{},'source_directory_postimages':lambda p:p['_closed_rows']}
exec(compile(module,'<ast-only-commands-for-plan>','exec'),ns)
objects=[]
for row in recipe['retained_inputs']:objects.append({'replace':False,'link_token':row['link_token'],'source':row['source']})
for s in ('rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o'):objects.append({'replace':True,'link_token':s})
post=[{'relative':'kernel/syscall.c','postimage':{'test':1}}];closed=[{'relative':'kernel/rust/lib.rs','postimage':{'test':2}}]
p={'request_sha256':'a'*64,'inputs':{'postimages':post,'objects':objects},'cohort_source_bindings':[{'relative':x['relative'],'postimage':x['postimage']} for x in post]+closed,'_closed_rows':closed,'reuse_descriptor':'/not-an-authority','producer_contract':{'process_delta':'inherited exact process object'},'exact_commands':copy.deepcopy(recipe['ordered_commands'])}
assert ns['commands_for_plan'](p)==recipe['ordered_commands']
mutations=[]
def rejected(label, mutate):
 q=copy.deepcopy(p);mutate(q)
 try:ns['commands_for_plan'](q)
 except (ValueError,KeyError):mutations.append(label)
 else:raise AssertionError(label+' was incorrectly accepted')
rejected('changed Rust argv',lambda q:q['exact_commands'][0]['argv'].append('--bad'))
rejected('changed arch object identity',lambda q:next(r for r in q['inputs']['objects'] if r['link_token'].endswith('arch/x86_64/kernel/syscall.c.o'))['source'].__setitem__('sha256','0'*64))
rejected('missing generic object replacement',lambda q:q['inputs']['objects'].pop())
rejected('changed raw link order',lambda q:q['exact_commands'][2]['argv'].reverse())
rejected('bad source binding',lambda q:q['cohort_source_bindings'].pop())
result={'status':'PASS_THREE_COMMAND_SOURCE_AND_FAIL_CLOSED_MUTATIONS','snapshot_rows_authenticated':149,'unchanged_operation_guards':['resource_guards','mounts','docker_prefix','docker_argv','current_operation_guard','execute_except_new_container_name'],'positive_commands_for_plan':True,'rejected_mutations':mutations,'runtime_authority':None,'actual_compiler_native':False}
(D/'PURE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
# Sealer is statically checked only: root controls, reviewer identities, guard
# and filesystem admission are not fabricated or invoked by this source check.
oldseal=(P/'seal_root_current119_inputs.py').read_text();seal=(D/'seal_root_conversion_inputs.py').read_text();ast.parse(seal)
a=" assert re.fullmatch('[0-9a-f]{32}'";b=' return limits,origin(q[\'origin_directory\'],q[\'origin_receipt\'])'
assert oldseal[oldseal.index(a):oldseal.index(b)+len(b)]==seal[seal.index(a):seal.index(b)+len(b)]
for required in ('accepted.accepted_metadata(oldq,oldfree,oldledger); accepted.accepted_chain(oldq)', 'PASS_EXACT_ROOT68_CURRENT119_CURRENT_BOUNDARY_ADOPTION', "len(ledger['consumed_nonces'])==73", "q['armed_controls']['path']==str(NEWSC/'ACTUAL-CONTROLS-ARMED.json')", "request['candidate']==CANDIDATE and request['recipe']==RECIPE and request['snapshot_map']==SNAPSHOT_MAP", "len(manifest['files'])==149", "row['snapshot']['sha256']==source['sha256']", "assert set(actual)==set(expected)"):
 assert required in seal
print('PASS_STATIC_SEALER_CHAIN_AND_WEEKLY_GUARDS_UNINVOKED')
