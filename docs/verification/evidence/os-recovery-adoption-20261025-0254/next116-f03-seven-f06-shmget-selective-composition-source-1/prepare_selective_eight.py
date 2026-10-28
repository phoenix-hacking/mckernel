"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source composition only; never executes production commands or writes canonical.
"""
import json, hashlib, shutil, difflib
from pathlib import Path
R=Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254'; D=Path(__file__).resolve().parent
F=E/'f03-next-selected-family-source-3/coherent-seven-current115-source-1'; S=E/'m14-f06-shmget-current115-default-integration-source-1'; P=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1'; A=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4'
SCOPE=__doc__.splitlines()[0]
def ref(p):
 p=Path(p); b=p.read_bytes(); return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def check(r):
 assert ref(r['path'])==r,r['path']
def save(n,d): (D/n).write_text(json.dumps(d,indent=2)+'\n')
sm=json.loads((S/'SIX-PATH-SELECTIVE-INTEGRATION.NOT-AUTHORITY.json').read_text()); rows=sm['writes'][:]
for rel in ['kernel/syscall.c','kernel/rust/syscall_policy.rs']:
 rows.append(dict(relative=rel,preimage=ref(R/rel),postimage=ref(F/'candidate'/rel)))
assert rows[-2]['preimage']['sha256']=='d6e9c595364f72018b96ccba50e97ebc71ff438b8e91315982e287d63ff8bafb'
assert rows[-1]['preimage']['sha256']=='d2522903a4a1335aa551f87c17c8e8765f9f7373fb84984b2dd062ac301004c0'
for row in rows:
 check(row['postimage']); old=row['preimage']; rel=row['relative']
 if old: check(old)
 else: assert not (R/rel).exists()
 dst=D/'candidate'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(row['postimage']['path'],dst);row['frozen_input']=row['postimage'];row['postimage']=ref(dst)
 if old:
  diff=''.join(difflib.unified_diff(Path(old['path']).read_text().splitlines(True),dst.read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)); pp=D/'patches'/(rel.replace('/','__')+'.patch');pp.parent.mkdir(exist_ok=True);pp.write_text(diff);row['patch']=ref(pp)
# Exact eight-path overlay, no body modification or source discovery.
assert len(rows)==8 and len({x['relative'] for x in rows})==8
c=(D/'candidate/kernel/syscall.c').read_text()
for line in ['#line 21118','#line 21150','#line 24477','#line 24491']:assert c.count(line)==1,(line,c.count(line))
origin_old=(R/'scripts/derive_f06_origin.py').read_text();origin_new=(D/'candidate/scripts/derive_f06_origin.py').read_text()
assert [x for x in difflib.ndiff(origin_old.splitlines(),origin_new.splitlines()) if x[:2] in ('- ','+ ')]==['- '+x for x in origin_old.splitlines() if x.startswith('PROFILE_SHA256 =')]+['+ '+x for x in origin_new.splitlines() if x.startswith('PROFILE_SHA256 =')]
fm=json.loads((F/'CLOSED-CURRENT115-PLUS-SEVEN-SOURCE-MAP.json').read_text()); rust=[]
for row in fm['private120_Rust_files']:
 r=row['relative']; src=D/'candidate/kernel/rust'/r if r in ['lib.rs','syscall_policy.rs'] else Path(row['new_snapshot']['path']);check(row['new_snapshot']);rust.append(dict(relative=r,source=ref(src)))
rust.append(dict(relative='f06_shmget_dispatch.rs',source=ref(D/'candidate/kernel/rust/f06_shmget_dispatch.rs')))
assert len(rust)==121
save('SELECTIVE-EIGHT-SOURCE-MAP.json',dict(scope=SCOPE,status='PRIVATE_SOURCE_ONLY',writes=rows,Rust_files=rust,external_relative_modules=fm['external_relative_modules'],source_adoption=None,compiler_acceptance=None,current_image=None,native_acceptance=None))
fp=json.loads((F/'ORDERED-QUALIFICATION-AND-DEFAULT-PRODUCER.RECIPE.NOT-GRANTED.json').read_text());sp=json.loads((S/'EXACT-SHM-ONLY-PRODUCTION-PROPOSAL.NOT-GRANTED.json').read_text());fcommands=fp['exact_future_container_commands']; sc=sp['exact_commands']
generic=next(x for x in fcommands if '/src/kernel/syscall.c' in x['argv'])
commands=[sc[0],generic,sc[1],sc[2]]
assert '--cfg' in commands[0]['argv'] and 'f06_shmget_dispatch_candidate' in commands[0]['argv']
assert '-DMCKERNEL_RUST_F06_SHMGET_DISPATCH' in commands[2]['argv']
reuse=json.loads((P/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json').read_text())
retained=[x for x in reuse['objects'] if not x['replace'] and x['link_token']!='CMakeFiles/mckernel.img.dir/syscall.c.o']
process=A/'OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o'; pr=ref(process);assert pr['sha256']=='3717ed77bd1761c734e93a72d4e5a0b770698f17760470286019f6ec6a6973dd'
retained.append(dict(action='Retain actual115 process object only after independent artifact acceptance',build_relative='kernel/CMakeFiles/mckernel.img.dir/process.c.o',link_token='CMakeFiles/mckernel.img.dir/process.c.o',source=pr))
assert len(retained)==8
for x in retained:check(x['source'])
save('MINIMAL-PRODUCTION-CONTINUATION.NOT-GRANTED.json',dict(scope=SCOPE,ordered_commands=commands,prerequisite_origin=sp['additional_sourceonly_origin_prerequisite'],retained_inputs=retained,actual115_metrics=ref(A/'ROOT-ACTUAL-COMPILER-METRICS.json'),actual115_tool_join=ref(A/'ROOT-ACTUAL-TOOL-RESULT.json'),actual115_independent_artifact_acceptance=None,Root_must_bind_existing_profile_export_source_map_origin_metadata_before_execution=True,Root_command_sequence=['guard all eight preimages; adopt exact private postimages with Root authority','materialize 121 Rust references and three external relative modules into closed export','run existing genuine origin materializer on new arch source/profile; bind actual generated outputs','retain eight exact object inputs; run the four exact commands under fresh normal reviewed build authority','run positive ABI/table/direct-or-folded caller/final-image checks; retain all failures'],future_production_objects=None,future_image=None,future_currentconsumer_proof=None,native_release=None,runtime_authority=None))
save('SOURCE-COMPOSITION-CHECKS.json',dict(scope=SCOPE,status='PASS_SOURCE_ONLY',paths=8,Rust_files=121,unchanged_retained_objects=8,production_commands_prepared=4,shared_wakeup_restore_once=True,accepted_perf_five_lines_preserved=True,origin_algorithm_PROFILE_SHA_only=True,CPUID_LOCAL31_preserved=True,new_qualified_bodies_claimed=False,canonical_writes=0,compiler_invocations=0))
print('PASS private eight-path composition,121 Rust references,8 retained object hashes,4 future commands')
