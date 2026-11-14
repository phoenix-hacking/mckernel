"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only bounded suffix validation/seal; no compiler/linker/admission execution.
"""
from pathlib import Path
import json,hashlib,importlib.util,ast,os
P=Path(__file__).resolve().parent;F=P.parent;E=F.parent
old=json.loads((F/'PROFILE.NOT-GRANTED.json').read_text());recipe=json.loads((P/'SUFFIX-RECIPE.NOT-ADMITTED.json').read_text());diagnosis=json.loads((P/'RETAINED-LINKER-DIAGNOSIS.json').read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
oldout=F/'HOST-output-proposed-1';out=P/'HOST-output-proposed-2';capture=P/'future-capture-2';assert not os.path.lexists(out) and not os.path.lexists(capture)
q=(P/'qualify_retained_metadata.py').read_text();original=(F/'qualify_metadata.py').read_text()
q=q.replace('out=Path(sys.argv[1]);joint_out=Path(sys.argv[2]);file=','out=Path(sys.argv[1]);file=',1).replace("joint=m.Elf(joint_out/('joint'+str(flags)+'.o'))","joint=m.Elf(out/('joint'+str(flags)+'.o'))",1).replace("(P.parent/'RETAINED-CONSUMER-EVIDENCE.json')","(P/'RETAINED-CONSUMER-EVIDENCE.json')",1).replace('P=Path(__file__).resolve().parent;E=P.parent.parent','P=Path(__file__).resolve().parent;E=P.parent',1).replace("(joint_out/'METADATA-QUALIFICATION.json')","(out/'METADATA-QUALIFICATION.json')",1)
assert q==original,'Any non-binding qualifier change is forbidden'
assert (P/'NEGATIVE-CONTROLS.NOT-ADMITTED.json').read_text().replace(str(out),str(oldout))==(F/'NEGATIVE-CONTROLS.NOT-ADMITTED.json').read_text()
for p in [P/'prepare_suffix.py',P/'seal_suffix.py',P/'qualify_retained_metadata.py']:ast.parse(p.read_text())
profile={k:old[k] for k in ['scope','goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes']};profile.update(task_id='NEW12H-ORDINARY-HOST-F02-VERBOSE32-RETAIN-SUFFIX-2',status='SOURCE_PROFILE_NOT_GRANTED',capture_root=str(capture),production_acceptance=False,LOCAL14_selected=False,retained_steps0_to7_no_replay=True,original_joint_outputs_failed=True,internal_and_capture_bound_bytes=2112*2**20,invocation_requirement='ABSOLUTE profile and grant paths')
commands=[]
for c in recipe['commands']:
 a=c['argv'];commands.append(dict(id=c['name'],argv=a,purpose=c['purpose'],cwd=str(P),timeout_seconds=90,stdout_limit_bytes=16384,stderr_limit_bytes=16384,requires_fresh_Root_ordinary_grant=True,leaf='F02verbose32retainSuffix',argv_compact_json_LF_sha256=hashlib.sha256((json.dumps(a,separators=(',',':'))+'\n').encode()).hexdigest()))
profile['commands']=commands;profile['leaves']=[dict(name='F02verbose32retainSuffix',first=0,last=3,plan=ref(P/'SUFFIX-RECIPE.NOT-ADMITTED.json'),output=str(out),expected_stdout=recipe['expected_stdout'])]
inputs={x['path']:x for x in old['inputs']}
for p in P.rglob('*'):
 if p.is_file() and p.name not in ['PROFILE.NOT-GRANTED.json','SOURCE-READY.json']:inputs[str(p)]=ref(p)
prefix=json.loads((P/'RETAINED-PREFIX-AND-FAILURE.json').read_text())
for row in prefix['retained_objects']+prefix['captures']+[prefix[x] for x in ['original_profile','root_tool','results','failure','original_qualifier']]:inputs[row['path']]=row
lld=Path(diagnosis['correction_linker']['path']);root=lld.parents[4]
paths=[lld,root/'bin/rustc',root/'lib/rustlib/manifest-rustc-x86_64-unknown-linux-gnu',root/'lib/rustlib/multirust-channel-manifest.toml',root/'lib/libLLVM.so.21.1-rust-1.92.0-stable',Path(diagnosis['prior_real_qualified_Rust192_LLD2113']['path']),Path(diagnosis['production_toolchain']['path']),Path('/var/lib/dpkg/status'),Path('/var/lib/dpkg/info/binutils-x86-64-linux-gnu.list'),Path('/var/lib/dpkg/info/binutils-x86-64-linux-gnu.md5sums')]
for lib in ['libpthread.so.0','libz.so.1','libm.so.6','libgcc_s.so.1','libc.so.6','ld-linux-x86-64.so.2','libstdc++.so.6','libdl.so.2','librt.so.1','libtinfo.so.6']:
 p=Path('/lib/x86_64-linux-gnu')/lib;assert p.exists();paths.append(p)
for p in paths:inputs[str(p)]=ref(p)
profile['inputs']=list(inputs.values());(P/'PROFILE.NOT-GRANTED.json').write_text(json.dumps(profile,indent=2)+'\n')
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';s=importlib.util.spec_from_file_location('existing_runner',runner);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validate_profile(profile);m.verify(profile['inputs']+[x['plan'] for x in profile['leaves']])
ready=dict(scope=profile['scope'],status='SOURCE_ONLY_FOUR_COMMAND_LINKER_SUFFIX_READY',profile=ref(P/'PROFILE.NOT-GRANTED.json'),recipe=ref(P/'SUFFIX-RECIPE.NOT-ADMITTED.json'),retained_prefix=ref(P/'RETAINED-PREFIX-AND-FAILURE.json'),diagnosis=ref(P/'RETAINED-LINKER-DIAGNOSIS.json'),runner=ref(runner),inputs=len(inputs),commands=4,new_partial_links=2,new_successful_prefix_compiles=0,original_unrun_negative_controls=7,all_original_qualifier_guards_unchanged=True,negative_plan_only_output_paths_changed=True,positive_or_negative_compiler_linker_executed=False,guard_or_admission_executed=False,fresh_output_absent=True,fresh_capture_absent=True,native_delta=0,whole_file_delta=0)
(P/'SOURCE-READY.json').write_text(json.dumps(ready,indent=2)+'\n');print(json.dumps(ready))
