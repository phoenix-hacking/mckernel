"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One data-bound retained-artifact linker suffix; no actual compiler/linker execution.
"""
from pathlib import Path
import json,hashlib,re,importlib.util,struct,os,difflib
P=Path(__file__).resolve().parent;F=P.parent;E=F.parent;oldout=F/'HOST-output-proposed-1';cap=F/'future-capture-1';out=P/'HOST-output-proposed-2';capture=P/'future-capture-2'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,t):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
def js(n,x):save(n,json.dumps(x,indent=2)+'\n')
assert not os.path.lexists(out) and not os.path.lexists(capture)
results=json.loads((cap/'RESULTS.json').read_text());assert len(results['results'])==9
for r in results['results'][:8]:
 j=r['join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
assert results['results'][8]['join']['returncode']!=0 and not (cap/'step9').exists()
# Observe actual section transitions using the existing retained ELF reader.
spec=importlib.util.spec_from_file_location('f02_existing_elf',E/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
observations=[]
for filename in ['rust0.o','rust1.o','selected0.o','selected1.o','joint0.o','joint1.o']:
 e=m.Elf(oldout/filename);obj=e.definitions('process_ptrace_traceme_debug');verbose=[dict(flags=z['flags'],bytes=z['size'],alignment=z['align']) for z in e.sections if z['name']=='__verbose'];observations.append(dict(artifact=ref(e.path),verbose_sections=verbose,target_section_flags=[e.sections[x['ndx']]['flags'] for x in obj]))
assert observations[0]['target_section_flags']==observations[1]['target_section_flags']==[0x200003]
assert observations[4]['target_section_flags']==observations[5]['target_section_flags']==[3]
# Linker/version provenance is read as metadata only, never --version execution.
oldld=Path('/usr/bin/ld');status=Path('/var/lib/dpkg/status').read_text();package=next(x for x in status.split('\n\n') if x.startswith('Package: binutils-x86-64-linux-gnu\n'));assert 'Version: 2.34-6ubuntu1.11' in package and b'(GNU Binutils for Ubuntu) 2.34' in oldld.read_bytes()
lld=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld');assert ref(lld)['sha256']=='5cd8306e6589847a21f0430ea0842f3305fb6ec83fefa6ce8a42e83a63576c82'
version=re.search(rb'LLD 21\.1\.3 \(/checkout/src/llvm-project/llvm [0-9a-f]+\)',lld.read_bytes()).group().decode()
root=lld.parents[4];manifest=root/'lib/rustlib/manifest-rustc-x86_64-unknown-linux-gnu';assert 'file:lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld' in manifest.read_text()
accepted=E/'f05-causal-rust-supervisor-host-qualification-1/independent-actual-review-1/REVIEW.json';qual=json.loads(accepted.read_text());assert qual['decision']=='PASS_ACTUAL_F05_RUST_CAUSAL_SUPERVISOR_HOST_SOURCE_ARTIFACT_QUALIFICATION';assert version in json.dumps(qual)
prod=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json');production=json.loads(prod.read_text());production_ld=production['image_tools']['ld'];assert '2.41-63.el10' in production_ld['version']
js('RETAINED-LINKER-DIAGNOSIS.json',dict(scope=__doc__.splitlines()[0],decision='OBSERVED_HOST_LD_R_SECTION_RETAIN_LOSS_NOT_RUST_SOURCE_FAILURE',observations=observations,old_linker=ref(oldld),old_linker_resolved=str(oldld.resolve()),dpkg_package=package,production_toolchain=ref(prod),production_linker=production_ld,correction_linker=ref(lld),embedded_version=version,component_manifest=ref(manifest),prior_real_qualified_Rust192_LLD2113=ref(accepted),provenance_limit='Prior accepted Rust192 executable records embeddedLLD21.1.3; this packet newly pins the exact distribution rust-lld bytes. No prior direct partial-link GNU_RETAIN qualification is claimed. The two future exact partial links must satisfy the unchanged guard.',cause_limit='Actual sealed Hostld2.34 operations mapped inputR flags0x200003 to output0x3. Productiontoolmanifest names different GNUld2.41. No generalized binutils source-cause or fixed-version claim is made.',linker_executed=False))
# Guard-preserving qualifier correction: only original-input vs new-joint paths.
q=(F/'qualify_metadata.py').read_text();newq=q.replace('out=Path(sys.argv[1]);file=', 'out=Path(sys.argv[1]);joint_out=Path(sys.argv[2]);file=',1)
newq=newq.replace("joint=m.Elf(out/('joint'+str(flags)+'.o'))","joint=m.Elf(joint_out/('joint'+str(flags)+'.o'))",1)
newq=newq.replace("(P/'RETAINED-CONSUMER-EVIDENCE.json')","(P.parent/'RETAINED-CONSUMER-EVIDENCE.json')",1)
# Module/E paths also need their actual original-family binding after relocation.
newq=newq.replace('P=Path(__file__).resolve().parent;E=P.parent','P=Path(__file__).resolve().parent;E=P.parent.parent',1)
newq=newq.replace("(out/'METADATA-QUALIFICATION.json')","(joint_out/'METADATA-QUALIFICATION.json')",1)
assert newq!=q and newq.count("assert joint.sections[ss['ndx']]['flags']&0x200000")==q.count("assert joint.sections[ss['ndx']]['flags']&0x200000")==1
save('qualify_retained_metadata.py',newq);save('qualifier-binding-only.diff',''.join(difflib.unified_diff(q.splitlines(True),newq.splitlines(True),fromfile='original/qualify_metadata.py',tofile='retained-inputs-new-joints/qualify_retained_metadata.py')))
# Exact original unrun negative controls, with ONLY output path substitutions.
oldneg=(F/'NEGATIVE-CONTROLS.NOT-ADMITTED.json').read_text();newneg=oldneg.replace(str(oldout),str(out));save('NEGATIVE-CONTROLS.NOT-ADMITTED.json',newneg)
commands=[]
for mode in [0,1]:commands.append(dict(name='0'+str(mode)+'-new-qualified-LLVM21-partial-link-flags'+str(mode),argv=[str(lld),'-flavor','gnu','-r',str(oldout/('selected'+str(mode)+'.o')),str(oldout/('rust'+str(mode)+'.o')),'-o',str(out/('joint'+str(mode)+'.o'))]))
commands += [dict(name='02-unchanged-retain-qualifier-retained-prefix-new-joints',argv=['/usr/bin/python3','-B',str(P/'qualify_retained_metadata.py'),str(oldout),str(out)]),dict(name='03-original-unrun-negative7-output-successor',argv=['/usr/bin/python3','-B',str(F/'negative_controls.py'),str(P/'NEGATIVE-CONTROLS.NOT-ADMITTED.json')])]
for command in commands:command['purpose']=__doc__.splitlines()[0]+' '+command['name']
recipe=dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_FOUR_COMMAND_SUFFIX_NOT_GRANTED',commands=commands,expected_stdout='VERBOSE32 PASS 7 bounded missing/mismatch/local14 controls\n',prefix_preserved_steps=list(range(8)),first_failed_step=8,original_unrun_step=9,old_joint_outputs_remain_failed=True,new_compile_positive_prefix_replay=0)
js('SUFFIX-RECIPE.NOT-ADMITTED.json',recipe)
js('RETAINED-PREFIX-AND-FAILURE.json',dict(scope=recipe['scope'],original_profile=ref(F/'PROFILE.NOT-GRANTED.json'),root_tool=ref(F/'ROOT-ACTUAL-TOOL-RESULT.json'),results=ref(cap/'RESULTS.json'),failure=ref(cap/'FIRST-FAILURE.json'),original_qualifier=ref(F/'qualify_metadata.py'),retained_objects=[ref(x) for x in sorted(oldout.glob('*.o'))],captures=[ref(x) for x in sorted(cap.rglob('*')) if x.is_file()],ordinary_prefix_steps_0_to_7_passed=True,negative7_unrun=True))
print(json.dumps(dict(status='source-only correction prepared',linker=str(lld),embedded_version=version,commands=4,positive_compile_replays=0)))
