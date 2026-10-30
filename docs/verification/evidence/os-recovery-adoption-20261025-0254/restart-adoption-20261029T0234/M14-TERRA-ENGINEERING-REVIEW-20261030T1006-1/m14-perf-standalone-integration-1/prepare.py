#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,pathlib,re,shutil,subprocess
A=pathlib.Path(__file__).resolve().parent.parent;O=pathlib.Path(__file__).resolve().parent;prior=A/'m14-nonheld-composition-1';composite=A/'m14-root-and-nonheld-composite-1';candidate=A/'m14-perf-standalone-host-failure-1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior_manifest=prior/'MANIFEST.json';comp_manifest=composite/'MOUNT-MANIFEST.json';patch=candidate/'candidate.patch'
assert sha(prior_manifest)=='ad611913d8965e1140443c29678c2e1180a90a91095ea0141929b8767a92ada7'
assert sha(comp_manifest)=='8cb23a435a512bff5cc8a80d28fe9c70764ef047918c60722e535fa721738593'
assert sha(patch)=='2bd0c4921601bb6fed64e05cd91762947277fc7dbc9a6469239af1176e890fd4'
m=json.loads(prior_manifest.read_text());c=json.loads(comp_manifest.read_text());r=pathlib.Path(c['on_source_mount_proposal']['/src/kernel/rust']);rel='kernel/rust/f03_perf_group_cleanup.rs';pre=r/'f03_perf_group_cleanup.rs';mirror=prior/'postimage'/rel
prehash='0dc2c777c39a9b2f31bc5e3d80badd2d3de8db35bcd0adba205776bb58517293';posthash='7b13e1975636f0c496394e4fb6b0243ae926837a03099a498a69b9c3ab04b8b1'
assert m['rust_regular_file_hashes']['f03_perf_group_cleanup.rs']==prehash and sha(pre)==sha(mirror)==prehash and pre.is_file() and not pre.is_symlink()
cm=composite/'postimage/kernel/CMakeLists.txt';generic=pathlib.Path(c['on_source_mount_proposal']['/src/kernel/syscall.c']);policy=r/'syscall_policy.rs';entry=r/'f03_perf_entry_candidate.rs'
expected={cm:'f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655',generic:'4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4',policy:'11d9d9e14c6c4ee3d593083ce18137414a7780c23507a44fb0834937fa9618e4',entry:'d542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5'}
for p,h in expected.items():assert sha(p)==h,(p,sha(p))
cs=cm.read_text();g=generic.read_text();pol=policy.read_text();e=entry.read_text()
assert re.search(r'option\(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL\s+"[^"]+"\s+OFF\)',cs)
assert re.search(r'if\s*\(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL\)\s*list\(APPEND RUST_KERNEL_CFG\s+"--cfg"\s+"f03_perf_entry_candidate"',cs)
assert re.search(r'if\s*\(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL\)\s*set_property\(SOURCE\s+"\$\{CMAKE_CURRENT_SOURCE_DIR\}/syscall.c"\s+APPEND PROPERTY\s+COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL',cs)
assert '#if defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nextern long sys_perf_event_open' in g
assert '#[cfg(all(f03_perf_entry_candidate, enable_perf, target_arch = "x86_64"))]\n#[path = "f03_perf_entry_candidate.rs"]' in pol
assert '#[path = "f03_perf_group_cleanup.rs"]\nmod f03_perf_group_cleanup;' in pol and 'f03_perf_group_cleanup::perf_entry_with_group_cleanup' in e
for x in ('f03_sync_child_event_candidate','f03_leaf_callbacks_candidate','f03_perf_alloc_bridges_selected_candidate'):assert x in pol and x in cs,x
before=(O/'preimage'/rel);after=(O/'postimage'/rel)
for p in (before,after):p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(pre,p)
for root,dry in ((O/'preimage',True),(O/'postimage',False)):
 cmd=['patch','--batch','-p1','-d',str(root)]+(['--dry-run'] if dry else []);res=subprocess.run(cmd,input=patch.read_bytes(),capture_output=True);assert res.returncode==0,(cmd,res.stdout,res.stderr);(O/('dry-run.stdout' if dry else 'apply.stdout')).write_bytes(res.stdout);(O/('dry-run.stderr' if dry else 'apply.stderr')).write_bytes(res.stderr)
assert sha(before)==prehash and sha(after)==posthash and after.read_bytes()==(candidate/'postimage'/rel).read_bytes()
s0=before.read_text();s1=after.read_text();new='''        // Only a standalone event is still private: its leader points to\n        // itself and no sibling/descriptor published it. The selected counter\n        // provider has only scanned the allocation map, and the host helper\n        // returns before setting that map on this branch. Grouped events need\n        // a separately reviewed leader/reader lifetime and are left unchanged.\n        if group_fd == -1 {\n            unsafe { super::perf_event_alloc_free_bridge(event) };\n        }\n''';assert s1.count(new)==1 and s1.replace(new,'')==s0
report={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_ONLY_UNRELEASED','authority':None,'base_nonheld_manifest':{'path':str(prior_manifest),'sha256':sha(prior_manifest)},'base_composite_manifest':{'path':str(comp_manifest),'sha256':sha(comp_manifest)},'source_patch':{'path':str(patch),'sha256':sha(patch)},'preimage':{'path':str(pre),'sha256':prehash},'private_postimage':{'path':str(after),'sha256':posthash},'prospective_on_mount_delta':{'target':'/src/kernel/rust/f03_perf_group_cleanup.rs','host_candidate':str(after),'mode':'ro','live_identity':None,'parent_target':'/src/kernel/rust','parent_host_candidate':str(r),'requires':'existing file mountpoint, parent-before-child, separately authenticated source identity and mount review'},'paired_selection':{'cmake':str(cm),'cmake_sha256':sha(cm),'C':str(generic),'C_sha256':sha(generic),'Rust_policy':str(policy),'Rust_policy_sha256':sha(policy),'Rust_entry':str(entry),'Rust_entry_sha256':sha(entry),'option':'MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL','default':'OFF','cfg':'f03_perf_entry_candidate','C_define':'MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL','scope':'source selectors only, actual generated flags/ABI/link not established'},'unchanged_grouped_path':'entire file difference is the guarded group_fd == -1 insertion; this is a static source result, not proof of grouped lifetime safety','open':['host FD result or rollback semantics','group and close lifetime and concurrency','source and mount identity/quiescence','test admission, compile/link/default/native qualification and independent review']}
(O/'INTEGRATION.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact target preimage, paired source selectors, private dry-run/apply, exact postimage and standalone-only textual delta')
