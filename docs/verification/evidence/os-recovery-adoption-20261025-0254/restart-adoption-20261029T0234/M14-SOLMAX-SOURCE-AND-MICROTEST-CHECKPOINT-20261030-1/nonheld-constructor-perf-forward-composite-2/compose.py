#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded private source correction; no build, tests, physical work, or release.
"""
from pathlib import Path
import hashlib,json,difflib,re
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1');O=Path(__file__).resolve().parent;PRE=D/'nonheld-constructor-perf-forward-composite-1';E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234');B=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c';BP=E/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/syscall_policy.rs';BC=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert h(PRE/'PROFILE.SOURCE-ONLY.json')=='721511c937d369b75cc69d7c3689f8927d842c3f8c1d9a1281e147104991389e'
assert h(PRE/'NONHELD-CONSTRUCTOR-PERF-FORWARD.PRIVATE.patch')=='d7196c7633ace3c9c7d1a0a767c23f29fec71870bf9c07bd12e06ce6821ffe8a'
assert h(B)=='3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3'
p=json.loads((PRE/'PROFILE.SOURCE-ONLY.json').read_text());files={k:(PRE/'postimage'/k).read_text() for k in p['postimage_hashes']};assert len(files)==7
for k,v in p['postimage_hashes'].items():assert h(PRE/'postimage'/k)==v
base=B.read_text();current=files['kernel/syscall.c']
def line_at(src,at):
 n=1
 for row in src[:at].splitlines():
  m=re.match(r'^\s*#\s*line\s+(\d+)',row);n=int(m.group(1)) if m else n+1
 return n
def function(src,name):
 pattern=r'long\n'+name+r'\([^\n]*\)\n\{';m=re.search(pattern,src);assert m,name;i=m.start();j=src.index('\n}\n',m.end())+3;return i,j,src[i:j]
mask_i,mask_j,mask_body=function(base,'syscall_forward_rt_sigprocmask_bridge');act_i,act_j,act_body=function(base,'syscall_forward_sigaction_update_bridge')
# Rewrite exactly each inner selector and reset both body and first following baseline line.
def replace_guard(src,body,start_i,end_i,extern,next_anchor):
 guard='#if defined(MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n'+extern+'\n#else\n';assert src.count(guard)==1
 start=src.index(guard);end=src.index(next_anchor,start)
 replacement=guard+'#line '+str(line_at(base,start_i))+'\n'+body+'#endif\n#line '+str(line_at(base,end_i))+'\n'
 # next anchor begins with the original blank line; restores original successor.
 return src[:start]+replacement+src[end:]
current=replace_guard(current,mask_body,mask_i,mask_j,'extern long syscall_forward_rt_sigprocmask_bridge(unsigned long sigmask);','\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_getresuid')
current=replace_guard(current,act_body,act_i,act_j,'extern long syscall_forward_sigaction_update_bridge(int sig, const void *actp);','\nint do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact);')
# Parent policy-helpers OFF skips inner #line directives. Restore baseline at
# first line of its else arm, and once again unconditionally after parent endif.
outer='int do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact);\n#else\nint\ndo_sigaction';assert current.count(outer)==1 and base.count(outer)==1
bi=base.index(outer)+len('int do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact);\n#else\n');off_line=line_at(base,bi)
current=current.replace(outer,'int do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact);\n#else\n#line '+str(off_line)+'\nint\ndo_sigaction',1)
outer_end='\n}\n#endif\n\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic const struct syscall_mckfd_offsets';assert current.count(outer_end)==1 and base.count(outer_end)==1
bi=base.index(outer_end)+len('\n}\n#endif\n');after_line=line_at(base,bi)
current=current.replace(outer_end,'\n}\n#endif\n#line '+str(after_line)+'\n\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic const struct syscall_mckfd_offsets',1)
assert current.count(mask_body)==1 and current.count(act_body)==1
files['kernel/syscall.c']=current
# Original Rust and the other five source files are byte-identical to prior.
for k in files:
 if k!='kernel/syscall.c':assert files[k].encode()==(PRE/'postimage'/k).read_bytes()
assert len(files)==7
basefiles={k:'' for k in files};basefiles['kernel/syscall.c']=base;basefiles['kernel/CMakeLists.txt']=BC.read_text();basefiles['kernel/rust/syscall_policy.rs']=BP.read_text()
def diff(a,b,k):return ''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='a/'+k if a else '/dev/null',tofile='b/'+k))
patch=O/'NONHELD-CONSTRUCTOR-PERF-FORWARD.PRIVATE.patch';assert not patch.exists();patch.write_text(''.join(diff(basefiles[k],files[k],k) for k in files))
tree=O/'postimage';assert not tree.exists();tree.mkdir(mode=0o700)
for k,v in files.items():q=tree/k;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(v)
p['status']='PRIVATE_SEVEN_FILE_CORRECTED_SOURCE_ONLY_NOT_RELEASED';p['predecessor_profile']={'path':str(PRE/'PROFILE.SOURCE-ONLY.json'),'sha256':h(PRE/'PROFILE.SOURCE-ONLY.json')};p['patch']={'path':str(patch),'sha256':h(patch)};p['postimage_hashes']={k:h(tree/k) for k in files};p['signal_fallback_correction']={'qualified_mask_body_sha256':hashlib.sha256(mask_body.encode()).hexdigest(),'qualified_action_body_sha256':hashlib.sha256(act_body.encode()).hexdigest(),'body_exact_original':True,'logical_line_directives':{'mask_body_start':line_at(base,mask_i),'mask_after_body':line_at(base,mask_j),'action_body_start':line_at(base,act_i),'action_after_body':line_at(base,act_j),'policy_off_do_sigaction_start':off_line,'after_parent_endif':after_line},'method':'Original multiline C bodies copied byte-for-byte inside selector-off branches. #line restores each original function start and successor; policy-off branch gets its own reset and both policy configurations reconverge after parent endif. C/Rust actual preprocessor and emitted metadata remain open.'};p['known_limits'][0]='C preprocessing and emitted source metadata for actual paired and fallback branches require independent review and actual object proof; source bodies were restored byte-for-byte and #line intent is recorded.';p['source_check_history']='Prior source-candidate conditional review found two C fallback bodies compressed on one line; original candidate and review retained. This successor restores original bodies and logical-line resets.';p['compiler_test_native_run']=False;p['authority']=None
e=D/'request-constructor-microtest-profile-1/RESULT.ACTUAL.json';a=json.loads(e.read_text());assert a['status']=='PASS_ACTUAL_HOST_MOCK_ONLY' and a['files']['f03_request_constructors.rs']['sha256']=='759818c4bbf907f988b0e6a349221ec8356e8b2b6863ce36071d2fa8ca9b35a1' and a['files']['constructor_alignment_fixture.rs']['sha256']=='65052b04c27f597611b67b0b737c5c6e784376e47fd9bb9bc16f1ccbdb2d588a'
p['known_limits']=[x.replace('real witness suffix all-five 5c8f8550f97498b58d72bc12f05aafccdd80d749498bff7dc8a2eaf37b69b8fe and isolated fixture remain source-only, witness object excluded from final link','real-header all-five witness remains source-only and must be excluded from final link; host-mock fixture passed at its separately recorded scope') for x in p['known_limits']];p['constructor_host_mock']={'result':str(e),'sha256':h(e),'status':a['status'],'tests_passed':a['rust_tests_passed'],'actual_exports_exercised':a['actual_exports_exercised'],'limits':'Host-mock geometry/provider scope only; no production/header ABI, link or native acceptance.'}
f=O/'PROFILE.SOURCE-ONLY.json';f.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n');print(json.dumps({'patch_sha256':h(patch),'profile_sha256':h(f),'C_sha256':h(tree/'kernel/syscall.c'),'line_resets':p['signal_fallback_correction']['logical_line_directives']},indent=2))
