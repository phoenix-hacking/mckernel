#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private seven-file source composition. No compiler, test, physical or release operation.
"""
from pathlib import Path
import hashlib,json,re,difflib
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234');D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2');O=Path(__file__).resolve().parent
C=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c';CM=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt';P=E/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/syscall_policy.rs';prior=D/'perf-signal-selected-compositor-1/PERF-SIGNAL-COMBINED.PRIVATE.patch';profile=D/'perf-signal-selected-compositor-1/SELECTED-PROFILE.SOURCE-ONLY.json';leaf=D/'request-bridge-align64-source-1/f03_request_constructors.rs';bind=D/'request-bridge-align64-source-1/ALL5-ADDITIVE-SOURCE-BINDING.json';cw=D/'request-bridge-align64-source-1/REQUEST-BRIDGE-REAL-C-ABI.ALL5.c.inc';review=D/'request-bridge-align64-source-1/INDEPENDENT-SOURCE-REVIEW-20261030-1.md'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
exp={C:'3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3',CM:'30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd',P:'14881100a803a90b25950b0c56d6fff6642a4cc8614c895a87418c6b7540dc50',prior:'a5fb519d0a9cac9f00dc68c2d416a0322107b356fb96460066e87e230d173d34',profile:'5da2c29c8cec55ed788d5d9d66a08f135c4987cde0bafd8f88982b1c2e97f949',leaf:'759818c4bbf907f988b0e6a349221ec8356e8b2b6863ce36071d2fa8ca9b35a1',bind:'6639eb0e6d27f253378fec766255a516e63bdbbe44dd64c3a5597170d7575722',cw:'5c8f8550f97498b58d72bc12f05aafccdd80d749498bff7dc8a2eaf37b69b8fe'}
for p,v in exp.items():assert h(p)==v,(p,h(p))
def parse(p):
 raw=p.read_text().splitlines(keepends=True);fs=[];i=0
 while i<len(raw):
  assert raw[i].startswith('--- ') and raw[i+1].startswith('+++ ');l=raw[i][4:].strip();r=raw[i+1][4:].strip();i+=2;hs=[]
  while i<len(raw) and raw[i].startswith('@@ '):
   i+=1;a=[];b=[]
   while i<len(raw) and not raw[i].startswith(('@@ ','--- ')):
    x=raw[i];assert x[0] in ' +-'
    if x[0]!='+':a.append(x[1:])
    if x[0]!='-':b.append(x[1:])
    i+=1
   hs.append((a,b))
  fs.append((l,r,hs))
 return fs
def apply(src,hs):
 lines=src.splitlines(keepends=True)
 for a,b in hs:
  if not a:assert not lines;lines=b[:];continue
  hits=[i for i in range(len(lines)-len(a)+1) if lines[i:i+len(a)]==a];assert len(hits)==1,(len(hits),a[:2]);i=hits[0];lines[i:i+len(a)]=b
 return ''.join(lines)
base={'kernel/syscall.c':C.read_text(),'kernel/CMakeLists.txt':CM.read_text(),'kernel/rust/syscall_policy.rs':P.read_text(),'kernel/rust/f06_signal_log_budget.rs':'','kernel/rust/f03_perf_entry_candidate.rs':'','kernel/rust/f03_perf_group_cleanup.rs':'','kernel/rust/f03_signal_forward_defined_candidate.rs':''}
old=base.copy()
for _,right,hs in parse(prior):
 k=right.removeprefix('b/');assert k in old;old[k]=apply(old[k],hs)
# The inherited architecture signal candidate is unselected. Omit all of its
# source changes, including its extra module, while retaining selected perf and
# forwarding module declarations and all original architecture code.
marker='// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_perf_entry_candidate, enable_perf, target_arch = "x86_64"))]'
assert old['kernel/rust/syscall_policy.rs'].count(marker)==1
post={k:v for k,v in old.items() if k!='kernel/rust/f06_signal_log_budget.rs'}
post['kernel/rust/syscall_policy.rs']=base['kernel/rust/syscall_policy.rs']+'\n'+old['kernel/rust/syscall_policy.rs'].split(marker,1)[1].join([marker,''])
# equivalent explicit concatenation; keep the prior tail byte-for-byte.
assert post['kernel/rust/syscall_policy.rs'].endswith(old['kernel/rust/syscall_policy.rs'].split(marker,1)[1])
line='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_signal_log_budget.rs"\n';assert post['kernel/CMakeLists.txt'].count(line)==1;post['kernel/CMakeLists.txt']=post['kernel/CMakeLists.txt'].replace(line,'',1)
post['kernel/rust/f03_request_constructors.rs']=leaf.read_text();base['kernel/rust/f03_request_constructors.rs']=''
assert len(post)==7
# Install narrow constructor selector on real C fallback/forward declarations.
# Each #line restores the exact original logical location of original C tokens.
def current_line(src,at):
 n=1
 for x in src[:at].splitlines():
  m=re.match(r'^\s*#\s*line\s+(\d+)',x);n=int(m.group(1)) if m else n+1
 return n
def wrap(src,original,chosen):
 assert src.count(original)==1;at=src.index(original);begin=current_line(src,at);end=current_line(src,at+len(original))
 return src[:at]+'#if defined(MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)\n'+chosen+'\n#else\n#line '+str(begin)+'\n'+original+'#endif\n#line '+str(end)+'\n'+src[at+len(original):]
c=post['kernel/syscall.c']
protos='static long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0,\n\t\tunsigned long arg1);\nstatic long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0,\n\t\tunsigned long arg1, unsigned long arg2);\n'
c=wrap(c,protos,'extern long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1);\nextern long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2);')
wait_start='static int\nwait_host_wait4_bridge(int pid, int options)\n';assert c.count(wait_start)==1;i=c.index(wait_start);j=c.index('\n}\n',i)+3;wait=c[i:j];c=wrap(c,wait,'extern int wait_host_wait4_bridge(int pid, int options);')
start='static long\nsyscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0,\n\t\tunsigned long arg1)\n{';assert c.count(start)==1;i=c.index(start);end='\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic long\nsyscall_do_syscall_request_bridge';assert c.count(end)==1;j=c.index(end,i);block=c[i:j];assert all(x in block for x in ['syscall_policy_do_syscall2_bridge','syscall_do_syscall3_bridge','syscall_policy_do_syscall3_bridge']);begin=current_line(c,i);finish=current_line(c,j)
# Existing declarations above provide the selected symbols; fallback block is byte-identical.
c=c[:i]+'#ifndef MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS\n#line '+str(begin)+'\n'+block+'\n#endif\n#line '+str(finish)+'\n'+c[j:]
c+='\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#if defined(MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS) && (!defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(__x86_64__))\n#error "request constructors require matched x86 policy providers"\n#endif\n';post['kernel/syscall.c']=c
cm=post['kernel/CMakeLists.txt'];mark='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_signal_forward_defined_candidate.rs"\n';assert cm.count(mark)==1;cm=cm.replace(mark,mark+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_request_constructors.rs"\n',1)
mark='\t\t\t\tif (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n';assert cm.count(mark)==1;cm=cm.replace(mark,'\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")\n\t\t\t\tendif()\n'+mark,1)
mark='\n\t\t\tif (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n';assert cm.count(mark)==1;cm=cm.replace(mark,'\n\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)\n\t\t\tendif()\n'+mark,1);post['kernel/CMakeLists.txt']=cm
post['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_request_constructors_candidate, target_arch = "x86_64"))]\n#[path = "f03_request_constructors.rs"]\nmod f03_request_constructors;\n'
assert post['kernel/syscall.c'].count('MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS')==4
assert post['kernel/rust/f03_request_constructors.rs'].encode()==leaf.read_bytes()
assert len(post)==7 and len([k for k in post if k.startswith('kernel/rust/')])==5
for name in ['syscall_do_syscall2_bridge','syscall_policy_do_syscall2_bridge','syscall_do_syscall3_bridge','syscall_policy_do_syscall3_bridge','wait_host_wait4_bridge']:
 assert len(re.findall(r'pub unsafe extern "C" fn '+name+r'\b',leaf.read_text()))==1
# Original line!/file!/column! macro source coordinates must not move.
def loc(s):return [(n,m.start(),m.group()) for n,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b(?:line|file|column)!\s*\(',line)]
assert loc(base['kernel/rust/syscall_policy.rs'])==loc(post['kernel/rust/syscall_policy.rs'])
# No new held selections or held-specific source modifications.
for s in [post['kernel/CMakeLists.txt'],post['kernel/rust/syscall_policy.rs']]:
 assert 'f03_request_constructors_candidate' in s
assert 'MCKERNEL_FULL28_COMPILE_CANDIDATE' not in post['kernel/CMakeLists.txt']
# Build one unified patch without modifying any input source.
def diff(a,b,k):return ''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='a/'+k if a else '/dev/null',tofile='b/'+k))
patch=O/'NONHELD-CONSTRUCTOR-PERF-FORWARD.PRIVATE.patch';assert not patch.exists();patch.write_text(''.join(diff(base[k],post[k],k) for k in post))
# Materialize exactly the seven reviewed private source outputs, no full tree.
tree=O/'postimage';assert not tree.exists();tree.mkdir(mode=0o700)
for k,v in post.items():
 q=tree/k;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(v)
pr=json.loads(profile.read_text());r=pr['illustrative_raw_rust_argv'][:];ca=pr['illustrative_raw_C_argv'][:];assert r[-1]=='/src/kernel/rust/lib.rs' and ca[-1]=='/src/kernel/syscall.c'
r[-1:-1]=['--cfg','f03_request_constructors_candidate'];ca[-1:-1]=['-DMCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS']
assert all(not re.search(r'FULL28|terminate_host_whole|execveat_whole',z,re.I) for z in r+ca)
rows=['syscall_do_syscall2_bridge','syscall_policy_do_syscall2_bridge','syscall_do_syscall3_bridge','syscall_policy_do_syscall3_bridge','wait_host_wait4_bridge']
record={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SEVEN_FILE_SELECTED_SOURCE_ONLY_NOT_RELEASED','inputs':{str(p):h(p) for p in list(exp)+[review]},'patch':{'path':str(patch),'sha256':h(patch)},'preimage_hashes':{k:hashlib.sha256(v.encode()).hexdigest() if v else None for k,v in base.items() if k in post},'postimage_hashes':{k:h(tree/k) for k in post},'selectors':{'Rust':['f03_perf_entry_candidate','f03_signal_forward_defined_candidate','f03_request_constructors_candidate'],'C':['MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL','MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL','MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS'],'default':'all remain absent from qualified default; CMake request and signal variables are tested and unset false; perf is raw profile only','conditions':'x86_64 Linux6.12 non-UBSAN, selected policy/leaf/sync/perf providers, generated config.h with ENABLE_PERF and ordered include resolution; actual emitted flags and C/Rust pairing still unproven'},'constructor_names':rows,'caller_provider_scope':'Source-only reviewed C/Rust references cover wait4; time/clock/gettimeofday/nanosleep, scheduler, getitimer/setitimer, setfsuid/setfsgid, linux_mlock and munmap bridge paths. Policy wrappers accept unrestricted syscall numbers: exact final selected caller graph and held exclusions remain independently open. syscall_do_syscall2_bridge may be emitted as alias; inspect real unique provider and relocation rather than assume five distinct machine bodies. No constructor source restricts numbers.', 'architecture':'All previous cfg-inactive architecture-signal changes and added f06 log budget are omitted coherently; inherited actual baseline do_signal source retained byte-for-byte and selection remains OFF.', 'known_limits':['C syntax/logical locations after new conditional must receive independent review and actual preprocessor proof; unchanged C fallback text was retained exactly','original 389 metadata, all five ABI/provider/caller graph, selected Rust/C flags and real generated config, actual link uniqueness and off/on/mismatch builds not established','real witness suffix all-five '+h(cw)+' and isolated fixture remain source-only, witness object excluded from final link','matching ownership/functional/native proof and C retirement remain open'], 'illustrative_raw_rust_argv':r,'illustrative_raw_C_argv':ca,'link_argv_source_only':pr['link_argv_source_only'],'rebuilds':['full Rust crate rust/mckernel_rust.o','generic C kernel/CMakeFiles/mckernel.img.dir/syscall.c.o','fresh matching eleven-input raw link; nine unaffected objects only after exact fresh binding'], 'next':'Independent exact composite source/selector/ABI/caller review, then fresh Root70 current-free/resource and operation release before any compiler feedback.','compiler_test_native_run':False,'authority':None}
f=O/'PROFILE.SOURCE-ONLY.json';f.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'patch_sha256':h(patch),'profile_sha256':h(f),'postimage_hashes':record['postimage_hashes']},indent=2))
