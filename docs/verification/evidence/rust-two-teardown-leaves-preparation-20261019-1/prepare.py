from pathlib import Path
import json,hashlib,difflib,ast,copy
O=Path(__file__).parent;A=O.parent;T=Path('/home/holden/mckernel-work/host-preparation/rust-next-process-leaf-20261018-1');P=T/'production-integration-1';V=P/'retention-correction-1';F=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1');h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(A/'review-packet.json')=='fed7e32f2b0ccc2e0d25bd0a1b45087812ac7816f4d36924c7a3d7c90da794a2'
assert h(P/'review-packet.json')=='9173069dd2573c512c863a528ebd2b5da5c6185935535694be7e6bcf4efa121f'
assert h(V/'postbuild-14-INPUTS-v2.json')=='35bf4f7a4e174a570dc2917d9924cb8f86431f29dc165795adc8595de638f408'
paths=['kernel/process.c','kernel/rust/process_helpers.rs']
for f in paths:assert (P/'base'/f).read_bytes()==(A/'original'/f).read_bytes()
c=(P/'candidate/kernel/process.c').read_text();bodyC=(A/'frozen-time-account.c').read_text();assert c.count(bodyC)==1
c=c.replace(bodyC,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nvoid process_destroy_thread_time_account_bridge(void *thread_arg);\n#else\n'+bodyC+'#endif\n',1)
r=(P/'candidate/kernel/rust/process_helpers.rs').read_text();decl='    fn process_destroy_thread_time_account_bridge(thread: *mut c_void);\n';assert r.count(decl)==1;r=r.replace(decl,'',1)+(A/'time-account-body.rs').read_text()
assert (T/'release-tid-body.rs').read_text() in r and (A/'time-account-body.rs').read_text() in r
for n in ['pub unsafe extern "C" fn __release_tid','pub unsafe extern "C" fn process_destroy_thread_time_account_bridge','fn process_teardown_tsc_to_ts','fn process_teardown_ts_add']:assert r.count(n)==1
assert r.count('Some(process_destroy_thread_time_account_bridge)')==1 and r.count('Some(process_destroy_thread_release_tid_bridge)')==1
for f,content in [(paths[0],c),(paths[1],r)]:
 p=O/'candidate'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
patch=''.join(''.join(difflib.unified_diff((P/'base'/f).read_text().splitlines(True),(O/'candidate'/f).read_text().splitlines(True),fromfile='a/'+f,tofile='b/'+f)) for f in paths);(O/'candidate.patch').write_text(patch)
asserts=(P/'production-process-assertions.inc').read_text()+(A/'production-abi-assertions.inc').read_text();(O/'production-process-assertions.inc').write_text(asserts)
# Retain the exact reviewed prebuild function and extend only consumed ABI facts
# and symbol facts. Existing full native/legacy crates are still compiled once.
ext=(P/'production-driver-extension.py').read_text();old='RELEASE_TID_PROCESS_ASSERTIONS = '+repr((P/'production-process-assertions.inc').read_text());assert ext.count(old)==1;ext=ext.replace(old,'RELEASE_TID_PROCESS_ASSERTIONS = '+repr(asserts),1)
anchor="        if name == 'selected-process.o':";assert ext.count(anchor)==1
addition='''        time_definitions = [v for v in symbols if len(v) >= 4 and v[-1] == 'process_destroy_thread_time_account_bridge' and v[-2] == 'T']
        time_unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == 'process_destroy_thread_time_account_bridge' and v[-2] == 'U']
        _fail(len(time_definitions) == int(defined), 'normal time-account symbol definition ' + name)
        _fail(len(time_unresolved) == 0, 'normal time-account unresolved symbol ' + name)
'''
# selected process's time callback declaration has no C consumer: the real
# default binding is inside the full Rust crate, not an invented C relocation.
ext=ext.replace(anchor,addition+anchor,1);ext=ext.replace("'body_consumer_descriptor': 'PENDING_POSTBUILD'","'body_consumer_descriptor': 'PENDING_POSTBUILD', 'two_leaf_symbols': ['__release_tid', 'process_destroy_thread_time_account_bridge']",1);ast.parse(ext);(O/'production-driver-extension.py').write_text(ext)
base=F/'adapters/native_rust_exact_mckernel_image_offline.py';driver=base.read_text();call='                _validate_release_fp_regs_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)';assert driver.count(call)==1;modified=driver.replace(call,call+'\n                _validate_release_tid_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)',1);modified=modified.replace('\ndef main(argv=None):','\n'+ext+'\ndef main(argv=None):',1);ast.parse(modified)
(O/'driver-extension.patch').write_text(''.join(difflib.unified_diff(driver.splitlines(True),modified.splitlines(True),fromfile='a/adapters/native_rust_exact_mckernel_image_offline.py',tofile='b/adapters/native_rust_exact_mckernel_image_offline.py')))
# These templates compile the same complete process TU/full crates, so no extra
# compiler command, proof object, retention member or output ceiling is added.
commands=json.loads((P/'production-commands-INPUTS.json').read_text());commands['two_leaf_symbols']=['__release_tid','process_destroy_thread_time_account_bridge'];commands['assertion_source']=str(O/'production-process-assertions.inc');commands['driver_extension']=dict(path=str(O/'production-driver-extension.py'),sha256=h(O/'production-driver-extension.py'));(O/'production-commands-INPUTS.json').write_text(json.dumps(commands,indent=2)+'\n')
newroot=O/'FUTURE-image-preparation';oldroot=P/'FUTURE-image-preparation';plan=json.loads((V/'postbuild-14-INPUTS-v2.json').read_text())
def remap(v):
 if isinstance(v,str):return v.replace(str(oldroot),str(newroot))
 if isinstance(v,list):return [remap(x) for x in v]
 if isinstance(v,dict):return {k:remap(x) for k,x in v.items()}
 return v
plan=remap(plan);plan['status']='INPUTS_ONLY_COMBINED_TWO_LEAF_PRODUCTION_UNRUN';plan['oracle']+=['Actual normal Rust/image each uniquely define process_destroy_thread_time_account_bridge; selected process contains no C definition, full fallback keeps unchanged C body','Actual complete Rust default destroy_thread retains Some(process_destroy_thread_time_account_bridge); validate function-pointer binding or reviewed equivalent inlining from actual compiler output, never invent a required C relocation','Actual emitted time body preserves captured-proc update-lock/unlock and system-convert/add then user-convert/add, existing helper ABI and64-aligned node; independent body review from already-captured full Rust/image disassembly']
plan['changed_finite_retention']['two_leaf_update']='No new proof objects: same selected-process.o and fallback-process.o contain both leaf selections. Existing21members and caps unchanged.'
assert plan['changed_finite_retention']['total_members']==21 and plan['total_output_ceiling_bytes']==339738624
(O/'postbuild-14-INPUTS.json').write_text(json.dumps(plan,indent=2)+'\n')
facts=(P/'postbuild_leaf_facts.py').read_text();anchor=" for kind in ['process','image']:";assert facts.count(anchor)==1
addition=''' for kind in nms:
  defined=[v for v in nms[kind] if v[1]=='T' and v[2]=='process_destroy_thread_time_account_bridge']
  unresolved=[v for v in nms[kind] if v[1]=='U' and v[2]=='process_destroy_thread_time_account_bridge']
  assert len(defined)==(0 if kind=='process' else 1),(kind,defined)
  assert not unresolved,(kind,unresolved)
 timebody=body(captures[8],'process_destroy_thread_time_account_bridge')
 assert not re.search(r'\\b(?:[xyz]mm[0-9]+|st\\([0-7]\\)|xsave\\w*|xrstor\\w*)\\b',timebody)
'''
facts=facts.replace(anchor,addition+anchor,1).replace('body_disassembly=actualbody,native_acceptance=False','body_disassembly=actualbody,time_account_body_disassembly=timebody,native_acceptance=False');ast.parse(facts);(O/'postbuild_two_leaf_facts.py').write_text(facts)
bindings=dict(status='STATIC_COMPOSITION_ONLY',fixed_base='1e7 image retained process.c and b3 process_helpers.rs',base_files={f:dict(path=str(P/'base'/f),sha256=h(P/'base'/f),bytes=(P/'base'/f).stat().st_size) for f in paths},composed_files={f:dict(path=str(O/'candidate'/f),sha256=h(O/'candidate'/f),bytes=(O/'candidate'/f).stat().st_size) for f in paths},parent_packets=[dict(path=str(P/'review-packet.json'),sha256=h(P/'review-packet.json')),dict(path=str(V/'RESULT.json'),sha256=h(V/'RESULT.json')),dict(path=str(A/'review-packet.json'),sha256=h(A/'review-packet.json'))],root_review_status='Root reports independent0034 PASS on both leaf source boundaries and21member retention; no fabricated external report identity',source_operations=['Apply reviewed TID selection/prototype/logger and exact Rust append to fixed baseline','Apply reviewed time callback C selection/prototype, remove its old Rust extern once, append exact reviewed time body','Retain both original C bodies byte-identically under fallback','Preserve exactly existing default callbacks; use unique time ABI aliases'],semantic_suite_replayed=False,compiler_or_runtime=False)
(O/'source-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
print(json.dumps(dict(status='TWO_LEAF_SOURCE_COMPOSED',patch_sha256=h(O/'candidate.patch'),source_bindings_sha256=h(O/'source-bindings.json'),retention_members=21,compiler_commands_added=0,executed=False)))
