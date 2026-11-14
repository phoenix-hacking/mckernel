"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Format existing producer SOURCE/DATA only. Never guard/export/copy/compiler/runtime.
Root alone supplies actual snapshot, origin, control/current-free/nonce and grants.
"""
from pathlib import Path
import argparse,ast,copy,hashlib,json,re
D=Path(__file__).parent
BASES=json.loads((D/'REUSED-PRODUCER-BASES.json').read_text())
def ref(p):
 p=Path(p).resolve();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def readref(x):
 assert ref(x['path'])==x
 return json.loads(Path(x['path']).read_text())
def write(name,x):
 with (D/name).open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,indent=2)+'\n')
def main(ready,affected,delta,uti):
 candref=ref(ready);assert not candref['sha256'].startswith('af2106'),'stale pre-uti_desc full28 prohibited'
 candidate=readref(candref);amap=readref(ref(affected));flags=readref(ref(delta));u=readref(ref(uti))
 assert ref(uti)['sha256'].startswith('38ac0893'),'exact completed uti_desc owner required'
 assert candidate['runtime_authority'] is None and flags['runtime_authority'] is None
 assert flags['Rust']['remove_cfg']==[] and flags['generic_C']['remove_definitions']==[] and flags['arch_C']['remove_definitions']==[]
 assert flags['C_witness_option'] is False and flags['link']['C_ABI_probe_objects']==[]
 overlay=amap['file_overlay'];assert len({x['target'] for x in overlay})==len(overlay)
 for row in overlay:assert ref(row['source']['path'])==row['source']
 by={x['target']:x['source'] for x in overlay}
 policy=Path(by['kernel/rust/syscall_policy.rs']['path']).read_text();generic=Path(by['kernel/syscall.c']['path']).read_text()
 assert 'pub static mut uti_desc: CULong = 0;' in policy and 'F03_UTI_DESC_LINKAGE unsigned long uti_desc;' in generic
 # Preserve old149 closed subtree; substitute/add ONLY exact final compositor refs.
 oldmap=readref(BASES['old149_source_map']);rows={x['relative']:copy.deepcopy(x) for x in oldmap['entries']}
 assert len(rows)==149
 for target,source in by.items():
  if target.startswith('kernel/rust/'):rows[target.removeprefix('kernel/rust/')]=dict(relative=target.removeprefix('kernel/rust/'),source=source)
 for x in rows.values():assert ref(x['source']['path'])==x['source']
 closed=[rows[k]for k in sorted(rows)];N=len(closed);R=sum(x['relative'].endswith('.rs') for x in closed)
 profile3=readref(BASES['source3_profile']);orig4=readref(BASES['original4_recipe'])
 assert len(profile3['exact_commands'])==3 and len(orig4['ordered_commands'])==4
 # Preserve actual first3 Rust/generic/rawlink argv and exact119 arch command.
 commands=copy.deepcopy(profile3['exact_commands'][:2]+[orig4['ordered_commands'][2],profile3['exact_commands'][2]])
 for x in flags['Rust']['add_cfg']:
  if not any(commands[0]['argv'][i:i+2]==['--cfg',x]for i in range(len(commands[0]['argv'])-1)):
   commands[0]['argv'][-1:-1]=['--cfg',x]
 for idx,key in [(1,'generic_C'),(2,'arch_C')]:
  for x in flags[key]['add_definitions']:
   token='-D'+x
   if token not in commands[idx]['argv']:commands[idx]['argv'].insert(1,token)
 assert commands[3]==profile3['exact_commands'][2] and commands[3]['argv']==orig4['ordered_commands'][3]['argv']
 assert not any('ARCH5_ABI_WITNESS' in s or 'arch5_abi_witness_candidate'==s for c in commands for s in c['argv'])
 replacements=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']
 retained=[dict(link_token=x['link_token'],source=x['source'])for x in profile3['inputs']['objects'] if x['link_token'] not in replacements]
 assert len(retained)==8 and all(not x['replace'] for x in profile3['inputs']['objects'] if x['link_token'] not in replacements)
 recipe={'scope':candidate['scope'],'status':'FULL28_EXACT_FOUR_COMMAND_SOURCE_RECIPE_NOT_EXECUTION_AUTHORITY','candidate':candref,'affected':ref(affected),'compiler_delta':ref(delta),'uti_owner':ref(uti),'historical_bases':BASES,'ordered_commands':commands,'retained_inputs':retained,'replacement_objects':replacements,'unchanged_raw_link':True,'source_files':N,'rust_files':R,'SDK21_recompiled':False,'C_ABI_probe_link_inputs':[],'runtime_authority':None}
 write('FOUR-COMMANDS.SOURCE-ONLY.json',recipe)
 snap={'scope':candidate['scope'],'status':'ROOT_MUST_PUBLISH_FRESH_EXACT_READONLY_CLOSED_SNAPSHOT','candidate':candref,'old149_map':BASES['old149_source_map'],'affected':ref(affected),'entries':closed,'source_files':N,'rust_files':R,'external_relative_modules':profile3['inputs']['external_relative_modules'],'runtime_authority':None};write('SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json',snap)
 # Existing original4 worker retains actual one-heavy/clock/UID/CPU controls.
 write('build_only_worker.template.py',Path(BASES['original4_worker']['path']).read_text())
 runner=Path(BASES['source3_runner']['path']).read_text()
 start=runner.index('COMMAND_RECIPE_REF=');end=runner.index('\n',start);runner=runner[:start]+'COMMAND_RECIPE_REF='+repr(ref(D/'FOUR-COMMANDS.SOURCE-ONLY.json'))+runner[end:]
 runner=runner.replace("len(manifest['files'])==149 and sum(row['relative'].endswith('.rs') for row in manifest['files'])==138",f"len(manifest['files'])=={N} and sum(row['relative'].endswith('.rs') for row in manifest['files'])=={R}")
 runner=runner.replace('exact118 source closure123/112',f'exact full28 source closure{N}/{R}')
 # Only recipe/object/source map consumer changes; operational functions unchanged.
 start=runner.index('def commands_for_plan(profile):');end=runner.index('\ndef current_operation_guard():',start)
 block=runner[start:end]
 for old,new in [('nine-object/two-replacement','eight-object/three-replacement'),('conversion-first three argv','full28 four argv'),('inherited nine object hashes including current119 arch','inherited eight object hashes; changed arch rebuilt'),("'mckernel.img']","'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']"),("sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']"),("len(commands)==3,'exact three selected successor commands'","len(commands)==4,'exact four selected successor commands'"),('both changed compiler source paths','three changed compiler source paths'),("len(retained)==9 and sum(r['replace'] for r in profile['inputs']['objects'])==2,'nine accepted retained and two new objects'","len(retained)==8 and sum(r['replace'] for r in profile['inputs']['objects'])==3,'eight accepted retained and three new objects'"),('set(outputs[:2])','set(outputs[:3])'),('exact two selected replacement','exact three selected replacement'),('elif i==1:','elif i in (1,2):'),("recipe['ordered_commands'][2]['argv']","recipe['ordered_commands'][3]['argv']")]:
  assert old in block,old;block=block.replace(old,new)
 runner=runner[:start]+block+runner[end:];ast.parse(runner);write('run_build_only.template.py',runner)
 # Root fills all current fields via the already reviewed sealer; do not reuse69.
 params={'scope':candidate['scope'],'status':'SOURCE_FACTORY_PARAMETERS_NOT_GRANT','candidate':candref,'affected':ref(affected),'recipe':ref(D/'FOUR-COMMANDS.SOURCE-ONLY.json'),'snapshot_map':ref(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json'),'runner_template':ref(D/'run_build_only.template.py'),'worker_template':ref(D/'build_only_worker.template.py'),'holder_unchanged':BASES['unchanged_holder'],'actual_root_frontier_parameters':ref(D/'ROOT-CURRENT-FRONTIER.PARAMETERS.NOT-AUTHORITY.json'),'expected_fresh_nonce_frontier':'74 or later actual current ledger; source minimum historical73 is not fresh clearance','new_snapshot_manifest':None,'new_origin_receipt':None,'new_request':None,'new_reuse_descriptor':None,'runtime_authority':None}
 write('SOURCE-FACTORY-PARAMETERS.NOT-AUTHORITY.json',params)
 # References only; no snapshot materialization, command runner or guard imported.
 write('PROFILE-INPUTS.SOURCE-ONLY.json',{'scope':candidate['scope'],'status':'ROOT_MUST_RESEAL_EXISTING_PROFILE_WITH_FRESH_ACTUAL_BINDINGS','candidate':candref,'exact_commands':commands,'inputs':{'postimages':[dict(relative=t,postimage=s)for t,s in by.items() if not t.startswith('kernel/rust/')],'source_directory_map':ref(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json'),'external_relative_modules':profile3['inputs']['external_relative_modules'],'configuration':profile3['inputs']['configuration'],'source6153':profile3['inputs']['source6153'],'retained_seed':profile3['inputs']['retained_seed'],'toolchain_mounts':profile3['inputs']['toolchain_mounts'],'toolchain_manifest':profile3['inputs']['toolchain_manifest'],'toolchain_lock_sha256':profile3['inputs']['toolchain_lock_sha256'],'objects':[dict(x,replace=False)for x in retained]+[dict(link_token=t,replace=True,source=None)for t in replacements],'retained_count':8,'replaced_count':3},'inherited_producer_contract':profile3['producer_contract'],'note':'Inherited postbuild predicates/expected counters retain original historical scopes; require actual full28 ownership/original389/link validation rather than copying old counts into acceptance. Root must populate exact source config/origin/profile and guards.','request_sha256':None,'reuse_descriptor':None,'cohort_source_bindings':None,'runtime_authority':None})
 print(json.dumps({'candidate':candref,'source_files':N,'rust_files':R,'commands':4,'retained_objects':8,'replaced_objects':3}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--candidate-ready',required=True);ap.add_argument('--affected',required=True);ap.add_argument('--delta',required=True);ap.add_argument('--uti-owner',required=True);q=ap.parse_args();main(q.candidate_ready,q.affected,q.delta,q.uti_owner)
