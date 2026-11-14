#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
In-memory composition only; no source tree, compiler, native or selection change.
"""
from pathlib import Path
import difflib,hashlib,json,re
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234')
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2')
O=Path(__file__).resolve().parent
P=D/'nonheld-signal-perf-private-compositor-1/NONHELD-SIGNAL-PERF.PRIVATE.patch'
G=D/'perf-group-failure-source-1'; S=D/'perf-group-selector-correction-source-1'
policy=E/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/syscall_policy.rs'
cmake=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt'
full=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/attempt-0001/m14-full28-procfs-successor-1/postimage/kernel/rust/syscall_policy.rs')
profile=E/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1/current-frontier-successor-1/PROFILE.SOURCE-ONLY.json'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
expected={P:'a85728bd41682489e5a2b0152d6cc6e8d44b924a24d3f5e58ab70df86f89c104',policy:'14881100a803a90b25950b0c56d6fff6642a4cc8614c895a87418c6b7540dc50',cmake:'30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd',full:'7a86da31eba184380922a624c8e9ac562c58c7086f1b6f1d9183fe2d7a44b063',profile:'8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d',G/'PREIMAGE-ENTRY.rs':'9f53dceac6e97cf7c961780362de729b13573f547634e9f98859a494fb651bf7',G/'f03_perf_entry_candidate.rs':'d542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5',G/'f03_perf_group_cleanup.rs':'0dc2c777c39a9b2f31bc5e3d80badd2d3de8db35bcd0adba205776bb58517293',G/'ENTRY-REBIND.PRIVATE.patch':'3e6f873b57c0cad24305c13b6450d91b7be7ee1e59b876268cbe49ea9ea3efd2',G/'SYSCALL-POLICY-APPEND.rs.inc':'3806e5a170a00bd4699bc01e500e469cace93c37a187aa7522975f1d42695a63',S/'SYSCALL-POLICY-APPEND.rs.inc':'f3c3de8dc22156f50df2bf3865c228fef12da7996eb04701a9c7f857f7d4a629',S/'SELECTOR-DEPENDENCIES.PRIVATE.patch':'222a2fd04ef88e6cdcb685d9fe59b34738529e514a1b59ffe8230dea56669880'}
for p,d in expected.items():assert h(p)==d,(p,h(p))
def parse(p):
 raw=p.read_text().splitlines(keepends=True); files=[];i=0
 while i<len(raw):
  assert raw[i].startswith('--- ') and raw[i+1].startswith('+++ '); left=raw[i][4:].strip();right=raw[i+1][4:].strip();i+=2;hunks=[]
  while i<len(raw) and raw[i].startswith('@@ '):
   i+=1;old=[];new=[]
   while i<len(raw) and not raw[i].startswith(('@@ ','--- ')):
    x=raw[i];assert x[0] in ' +-'
    if x[0]!='+':old.append(x[1:])
    if x[0]!='-':new.append(x[1:])
    i+=1
   hunks.append((old,new))
  files.append((left,right,hunks))
 return files
def apply(src,hunks):
 lines=src.splitlines(keepends=True)
 for old,new in hunks:
  if not old:assert not lines;lines=new[:];continue
  hits=[i for i in range(len(lines)-len(old)+1) if lines[i:i+len(old)]==old];assert len(hits)==1,hits
  i=hits[0];lines[i:i+len(old)]=new
 return ''.join(lines)
oldpolicy=policy.read_text();oldcm=cmake.read_text()
files={'kernel/rust/syscall_policy.rs':oldpolicy,'kernel/CMakeLists.txt':oldcm,'kernel/rust/f06_signal_log_budget.rs':'','kernel/rust/f03_perf_entry_candidate.rs':''}
for left,right,hunks in parse(P):
 k=right.removeprefix('b/');assert k in files;files[k]=apply(files[k],hunks)
entry='kernel/rust/f03_perf_entry_candidate.rs';assert files[entry]==(G/'PREIMAGE-ENTRY.rs').read_text()
gp=parse(G/'ENTRY-REBIND.PRIVATE.patch');assert len(gp)==1
files[entry]=apply(files[entry],gp[0][2]);assert files[entry]==(G/'f03_perf_entry_candidate.rs').read_text()
sp=parse(S/'SELECTOR-DEPENDENCIES.PRIVATE.patch');assert len(sp)==1
assert apply((G/'SYSCALL-POLICY-APPEND.rs.inc').read_text(),sp[0][2])==(S/'SYSCALL-POLICY-APPEND.rs.inc').read_text()
files['kernel/rust/syscall_policy.rs']+='\n'+(S/'SYSCALL-POLICY-APPEND.rs.inc').read_text()
marker='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_entry_candidate.rs"\n';assert files['kernel/CMakeLists.txt'].count(marker)==1
files['kernel/CMakeLists.txt']=files['kernel/CMakeLists.txt'].replace(marker,marker+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_group_cleanup.rs"\n',1)
files['kernel/rust/f03_perf_group_cleanup.rs']=(G/'f03_perf_group_cleanup.rs').read_text()
def extract(s,name):
 m=re.search(r'\bfn\s+'+name+r'\s*\(',s);assert m,name
 i=s.index('{',m.start());n=1;j=i+1
 while n:
  if s[j]=='{':n+=1
  if s[j]=='}':n-=1
  j+=1
 return s[m.start():j]
ident={}
for name in ['perf_event_open_body_result','perf_event_open_entry_body_result','perf_event_open_group_body_result','perf_event_open_counter_body_result']:
 a=extract(oldpolicy,name);b=extract(full.read_text(),name);assert a==b,name;ident[name]=hashlib.sha256(a.encode()).hexdigest()
def loc(s):return [(n,m.start(),m.group()) for n,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b(?:line|file|column)!\s*\(',line)]
assert loc(oldpolicy)==loc(files['kernel/rust/syscall_policy.rs'])
assert not loc(files['kernel/rust/f03_perf_group_cleanup.rs'])
args=[x for q in json.loads(profile.read_text())['exact_commands'] for x in q['argv']];assert 'f03_perf_entry_candidate' not in args and '-DMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL' not in args
assert files['kernel/rust/syscall_policy.rs'].count('mod f03_perf_group_cleanup;')==1
assert 'perf_entry_counter_alloc_or_release' in files[entry] and 'f03_perf_group_cleanup::perf_entry_with_group_cleanup' in files[entry]
def diff(old,new,path):return ''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+path if old else '/dev/null',tofile='b/'+path))
out=O/'NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch';assert not out.exists()
out.write_text(diff(oldpolicy,files['kernel/rust/syscall_policy.rs'],'kernel/rust/syscall_policy.rs')+diff(oldcm,files['kernel/CMakeLists.txt'],'kernel/CMakeLists.txt')+''.join(diff('',files[k],k) for k in ['kernel/rust/f06_signal_log_budget.rs',entry,'kernel/rust/f03_perf_group_cleanup.rs']))
manifest={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'SOURCE_ONLY_PERF_ENTRY_OFF_NO_SELECTION_AUTHORITY','inputs':{str(p):h(p) for p in expected}|{str(G/'INDEPENDENT-SOURCE-REVIEW.md'):h(G/'INDEPENDENT-SOURCE-REVIEW.md'),str(S/'INDEPENDENT-SOURCE-REVIEW.md'):h(S/'INDEPENDENT-SOURCE-REVIEW.md')},'output':{'path':str(out),'sha256':h(out)},'checks':['prior private patch exact in-memory application','group entry rebind and selector correction exact preimage and output','four baseline perf functions byte-identical to the group review bound source', 'counter-failure wrapper retained, group dispatch present','source dependency registered','106 original Rust location macro coordinates preserved; copied group module contains none','qualified perf-entry Rust/C selectors remain absent; syscall C source unchanged'], 'identical_baseline_functions_sha256':ident,'selection':'Default qualified perf entry remains selected C; adding off-gated Rust source does not correct the default path or retire C. No C entry wiring or profile flag change provided. Rust cfg guard is not evidence of matching C flags.', 'open':['independent review of exact composite','C/Rust pairing and event binding with exact provider identities, ABI/layout, link uniqueness and metadata','provider-specific fresh/unpublished event ownership, thread/group/descriptor synchronization','group-success and later host, fd, allocation and rollback handling','signal ownership and native proof','source snapshot/profile/guard and operation-specific review before any build','held direct-TID/terminate_host and execve transfer/ACK excluded'], 'compiler_or_native_run':False,'authority':None}
(O/'COMPOSITION.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'patch_sha256':h(out),'manifest_sha256':h(O/'COMPOSITION.json'),'bytes':out.stat().st_size,'identical_functions':ident},indent=2))
