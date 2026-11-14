#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Make private three-command producer source data. No runtime or source export.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;E=A.parent
P=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119'
C=A/'M14-CONVERSION-FIRST-COMPOSITION-1'
recipe=E/'CURRENT119-JOINT-M14-REGISTRY-REPAIR-SOURCE-1/CURRENT119-FOUR-COMMANDS.NOT-GRANTED.json'
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert ref(C/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
assert ref(C/'AFFECTED-UNIT-CANDIDATE-INPUTS.json')['sha256']=='40756e0e6bfc1606a500bf97df7a27c48bd591ecb5bb8a1008a1ed51722a5bbe'
assert ref(recipe)['sha256']=='0c01ec0ee7b91decc9c6749fae8edf076f50e35f360f577bd3deac3d56edadfd'
affected=json.loads((C/'AFFECTED-UNIT-CANDIDATE-INPUTS.json').read_text());old=json.loads(recipe.read_text());profile=json.loads((P/'PROFILE.SOURCE-ONLY.json').read_text())
commands=[copy.deepcopy(old['ordered_commands'][i]) for i in (0,1,3)]
for i,c in enumerate(commands):c['id']=str(i);c.pop('argv_sha256',None)
rustflags=affected['required_Rust_cfg_additions'];cflags=affected['required_C_definitions_additions']
assert len(rustflags)==len(cflags)==3
argv=commands[0]['argv'];assert argv[-1]=='/src/kernel/rust/lib.rs'
for flag in rustflags:assert flag not in argv
argv[-1:-1]=[x for flag in rustflags for x in ('--cfg',flag)]
argv=commands[1]['argv'];assert argv[-2:]==['-c','/src/kernel/syscall.c']
for flag in cflags:assert '-D'+flag not in argv
argv[1:1]=['-D'+flag for flag in cflags]
for x in affected['forbidden_until_genuine_kfree_profile_proof']['Rust']:assert x not in commands[0]['argv']
for x in affected['forbidden_until_genuine_kfree_profile_proof']['C']:assert '-D'+x not in commands[1]['argv']
assert '--cfg' in commands[0]['argv'] and 'enable_perf' in commands[0]['argv']
assert '-DMCKERNEL_RUST_F03_LEAF_CALLBACKS' in commands[1]['argv'] and 'f03_leaf_callbacks_candidate' in commands[0]['argv']
retained=[r for r in affected['original_link_order'] if 'source'in r]
assert len(retained)==9 and len(affected['original_link_order'])==11
arch=[r for r in retained if r['link_token']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];assert len(arch)==1 and arch[0]['source']['sha256']=='30bddb4cf0e8083fcce83fe691410b6d4a0e8eabec3cb6ce3b6ab190be8ab3da'
assert commands[2]['argv']==old['ordered_commands'][3]['argv']
recipe_out={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_THREE_COMMAND_RECIPE_NOT_EXECUTION_AUTHORITY','predecessor':ref(recipe),'affected':ref(C/'AFFECTED-UNIT-CANDIDATE-INPUTS.json'),'ordered_commands':commands,'retained_inputs':retained,'runtime_authority':None}
(D/'THREE-COMMANDS.SOURCE-ONLY.json').write_text(json.dumps(recipe_out,indent=2)+'\n')
manifest=json.loads(Path(profile['inputs']['source_directory_exports'][0]['manifest']['path']).read_text())
assert len(manifest['files'])==133
maps={r['relative']:r['snapshot'] for r in manifest['files']}
for row in affected['producer_postimage_rows']:
 if row['relative'].startswith('kernel/rust/'):
  path=row['relative'].removeprefix('kernel/rust/');maps[path]=row['postimage']
assert len(maps)==149 and sum(k.endswith('.rs') for k in maps)==138
assert len(affected['producer_postimage_rows'])==20
source_map={'scope':recipe_out['scope'],'status':'ROOT_MUST_PUBLISH_EXACT_FRESH_CLOSED_SNAPSHOT','base_manifest':profile['inputs']['source_directory_exports'][0]['manifest'],'affected':ref(C/'AFFECTED-UNIT-CANDIDATE-INPUTS.json'),'entries':[{'relative':k,'source':v} for k,v in sorted(maps.items())],'source_files':149,'rust_files':138,'runtime_authority':None}
(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json').write_text(json.dumps(source_map,indent=2)+'\n')
runner=(P/'run_build_only.py').read_text();worker=(P/'build_only_worker.py').read_text()
# Reuse every operation/weekly/resource/mount control except the exact source
# closure cardinality and four-command/three-output recipe, which are replaced
# by data-bound three-command/nine-retained-object assertions.
runner=runner.replace("COMMAND_RECIPE_REF="+repr(eval((P/'run_build_only.py').read_text().split('COMMAND_RECIPE_REF=',1)[1].split('\n',1)[0])),"COMMAND_RECIPE_REF="+repr(ref(D/'THREE-COMMANDS.SOURCE-ONLY.json')))
runner=runner.replace("len(manifest['files'])==133 and sum(row['relative'].endswith('.rs') for row in manifest['files'])==122", "len(manifest['files'])==149 and sum(row['relative'].endswith('.rs') for row in manifest['files'])==138")
start=runner.index('def commands_for_plan(profile):');end=runner.index('\ndef current_operation_guard():',start)
new='''def commands_for_plan(profile):
    """Exact private affected-unit recipe; fresh actual Root binding required."""
    require(isinstance(profile['request_sha256'],str) and len(profile['request_sha256'])==64 and all(c in '0123456789abcdef' for c in profile['request_sha256']),'Root must bind new exact request SHA256')
    require(isinstance(profile['inputs']['postimages'],list) and profile['inputs']['postimages'],'Root must supply exact new readonly postimages')
    require(profile['cohort_source_bindings']==[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]+source_directory_postimages(profile),'exact new cohort source map')
    require(isinstance(profile['reuse_descriptor'],str) and profile['reuse_descriptor'],'Root must supply matching nine-object/two-replacement reuse descriptor')
    require(isinstance(profile['producer_contract']['process_delta'],str) and profile['producer_contract']['process_delta'],'Root must state exact new process delta')
    if 'unchanged_completed_process_prefix' in profile:require(profile['unchanged_completed_process_prefix']['Root_decision'] is not None,'Root must disposition already completed unchanged F02 process prefix before grant')
    commands=profile['exact_commands'];recipe=read(auth(COMMAND_RECIPE_REF))
    require(commands==recipe['ordered_commands'],'exact sealed conversion-first three argv recipe')
    retained=[r for r in profile['inputs']['objects'] if not r['replace']]
    require(sorted((r['link_token'],r['source']['sha256']) for r in retained)==sorted((r['link_token'],r['source']['sha256']) for r in recipe['retained_inputs']),'exact inherited nine object hashes including current119 arch')
    outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','mckernel.img']
    sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c']
    require(len(commands)==3,'exact three selected successor commands')
    require(set(s.removeprefix('/src/') for s in sources)<={r['relative'] for r in profile['inputs']['postimages']}|{r['relative'] for r in source_directory_postimages(profile)},'both changed compiler source paths must be bound readonly postimages')
    require(len(retained)==9 and sum(r['replace'] for r in profile['inputs']['objects'])==2,'nine accepted retained and two new objects')
    require({r['link_token'] for r in profile['inputs']['objects'] if r['replace']}==set(outputs[:2]),'exact two selected replacement object paths')
    for i,(command,output) in enumerate(zip(commands,outputs)):
        argv=command['argv'];require(isinstance(argv,list) and argv and all(isinstance(a,str) and a for a in argv),'exact nonempty literal argv')
        require(command['cwd']=='/work/output/build/kernel' and command['new_output']=='/work/output/build/kernel/'+output,'exact fixed output/cwd map')
        if i==0:require(argv[:3]==['/usr/bin/cmake','-E','env'] and '--emit=obj='+command['new_output'] in argv and argv[-1]==sources[i],'whole Rust object command binding')
        elif i==1:require(argv[0]=='/usr/bin/cc' and argv[-2:]==['-c',sources[i]] and argv[argv.index('-o')+1]==output,'exact selected C object/source command binding')
        else:require(argv==recipe['ordered_commands'][2]['argv'],'unchanged exact eleven-input raw link')
    return commands
'''
runner=runner[:start]+new+runner[end:]
runner=runner.replace("name='current119-build-build-only-'+grant['nonce']", "name='conversion-first-build-only-'+grant['nonce']")
worker=worker.replace("len(plan['commands'])==4,'exact four selected build commands'", "len(plan['commands'])==3,'exact three selected build commands'")
worker=worker.replace('ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER','ACTUAL_BUILD_ONLY_THREE_COMMAND_PRODUCER')
ast.parse(runner);ast.parse(worker)
(D/'run_build_only.template.py').write_text(runner);(D/'build_only_worker.template.py').write_text(worker)
for name in ('run_build_only.py','build_only_worker.py'):
 before=(P/name).read_text();after=(D/(name.replace('.py','.template.py'))).read_text()
 (D/(name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
r={'scope':recipe_out['scope'],'status':'PRIVATE_PRODUCER_SOURCE_DATA_PENDING_ROOT_SEAL_AND_REVIEW','original_runner':ref(P/'run_build_only.py'),'original_worker':ref(P/'build_only_worker.py'),'recipe':ref(D/'THREE-COMMANDS.SOURCE-ONLY.json'),'snapshot_map':ref(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json'),'runner_template':ref(D/'run_build_only.template.py'),'worker_template':ref(D/'build_only_worker.template.py'),'source_sealer':ref(P/'seal_root_current119_inputs.py'),'accepted_bindings':ref(P/'accepted_bindings.py'),'controls':'Unchanged weekly guard, three-clock cutoffs, CPU 2-5, 12GiB, 512-pid, one-heavy/27:4 resource and review predicates. Root68 current binding sealer successor remains required.', 'runtime_authority':None,'default_native_acceptance':False}
(D/'SOURCE-DATA.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
