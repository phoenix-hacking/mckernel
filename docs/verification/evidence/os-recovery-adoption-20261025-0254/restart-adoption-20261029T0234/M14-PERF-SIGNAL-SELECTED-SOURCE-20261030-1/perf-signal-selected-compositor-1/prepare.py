#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Hash-bound three-way source composition in memory; no build or materialization.
"""
from pathlib import Path
import hashlib,json,re,difflib
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234');D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2');O=Path(__file__).resolve().parent
C=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c';CM=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt';P=E/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/syscall_policy.rs';RP=D/'nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch';CP=D/'perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch';SP=E/'M14-REMAINING23-D-1/defined-callers-correction-1/SIGNAL-DEFINED-CALLERS.ON-FIRST20.PRIVATE-NOT-APPLIED.patch';SB=E/'M14-REMAINING23-D-1/defined-callers-correction-1/postimage/kernel/rust/f03_signal_forward_defined_candidate.rs'; prior=D/'perf-selected-composition-private-1/SELECTED-PROFILE.SOURCE-ONLY.json'; desc=D/'signal-forward-selector-abi-correction-1/SOURCE-PROFILE.md'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
exp={C:'3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3',CM:'30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd',P:'14881100a803a90b25950b0c56d6fff6642a4cc8614c895a87418c6b7540dc50',RP:'595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a',CP:'7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345',SP:'13d4813e5c8be05a33908e8c252f22bb7596e43ae55bf9390817feb3af118b2f',SB:'fa55a0ca4436c8b330221865db8ebe0a8481886a88a4212c817a197199b0c392',prior:'e3982185d18639c8874b009ffc20d23cb287fc1d2c607908049a5df758d3b13f',desc:'fced5d0b033bb5f54aca34c48e553f5c0ee666f179f9323e48da059e401db750'}
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
 l=src.splitlines(keepends=True)
 for a,b in hs:
  if not a:assert not l;l=b[:];continue
  hits=[i for i in range(len(l)-len(a)+1) if l[i:i+len(a)]==a];assert len(hits)==1,(hits,a[:2]);i=hits[0];l[i:i+len(a)]=b
 return ''.join(l)
base={'kernel/syscall.c':C.read_text(),'kernel/CMakeLists.txt':CM.read_text(),'kernel/rust/syscall_policy.rs':P.read_text(),'kernel/rust/f06_signal_log_budget.rs':'','kernel/rust/f03_perf_entry_candidate.rs':'','kernel/rust/f03_perf_group_cleanup.rs':'','kernel/rust/f03_signal_forward_defined_candidate.rs':''}
a=base.copy();b=base.copy()
for patch in [RP,CP]:
 for left,right,hs in parse(patch):
  k=right.removeprefix('b/');assert k in a;a[k]=apply(a[k],hs)
for left,right,hs in parse(SP):
 k=right.removeprefix('b/');assert k in b;b[k]=apply(b[k],hs)
assert b['kernel/rust/f03_signal_forward_defined_candidate.rs'].encode()==SB.read_bytes()
def merge(base,one,two):
 x=base.splitlines(keepends=True); edits=[]
 for owner,y in [('perf',one),('signal',two)]:
  for tag,i,j,k,l in difflib.SequenceMatcher(None,x,y.splitlines(keepends=True),autojunk=False).get_opcodes():
   if tag!='equal':edits.append((i,j,y.splitlines(keepends=True)[k:l],owner))
 edits.sort(key=lambda e:(e[0],e[1],e[3])); merged=[];pos=0;z=0
 while z<len(edits):
  i,j,v,owner=edits[z];assert i>=pos,(owner,i,j,pos);merged.extend(x[pos:i]);
  same=[edits[z]];z+=1
  while z<len(edits) and edits[z][0]==i and edits[z][1]==j and i==j:same.append(edits[z]);z+=1
  for _,_,v,_ in same:merged.extend(v)
  pos=j
 merged.extend(x[pos:]);return ''.join(merged)
combined={k:merge(base[k],a[k],b[k]) for k in base}
assert combined['kernel/rust/f03_signal_forward_defined_candidate.rs'].encode()==SB.read_bytes()
for k in base:
 if a[k]==base[k]:assert combined[k]==b[k]
 if b[k]==base[k]:assert combined[k]==a[k]
for patch in (RP,CP,SP):
 for line in patch.read_text().splitlines():
  if line.startswith(('+','-')) and not line.startswith(('+++','---')):assert not re.search(r'\b(execve|execveat|terminate_host|direct.tid)\b',line,re.I),line
def loc(s):return [(n,m.start(),m.group()) for n,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b(?:line|file|column)!\s*\(',line)]
assert loc(base['kernel/rust/syscall_policy.rs'])==loc(combined['kernel/rust/syscall_policy.rs'])
assert combined['kernel/CMakeLists.txt'].count('if (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL)')==2 and 'option(MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL' not in combined['kernel/CMakeLists.txt']
# Prove both compacted C fallbacks retain their original tokens.
def body(src,name):
 m=re.search(r'\b'+name+r'\([^;]*?\)\s*\{',src);assert m,name;i=src.index('{',m.start());n=1;j=i+1
 while n:
  n+=(src[j]=='{')-(src[j]=='}');j+=1
 return re.findall(r'\w+|[^\s]',src[m.start():j])
for name in ['syscall_forward_rt_sigprocmask_bridge','syscall_forward_sigaction_update_bridge']:assert body(base['kernel/syscall.c'],name)==body(combined['kernel/syscall.c'],name)
def logical(lines):
 n=1;o=[]
 for line in lines:o.append(n);m=re.match(r'^\s*#\s*line\s+(\d+)',line);n=int(m.group(1)) if m else n+1
 return o
old=base['kernel/syscall.c'].splitlines(keepends=True);new=combined['kernel/syscall.c'].splitlines(keepends=True);x=logical(old);y=logical(new)
for tag,i,j,k,l in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
 if tag=='equal':
  for ii,kk in zip(range(i,j),range(k,l)):
   if old[ii].strip() and not re.match(r'^\s*#\s*line\s+\d+',old[ii]):assert x[ii]==y[kk],(ii,kk,old[ii])
def diff(old,new,k):return ''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+k if old else '/dev/null',tofile='b/'+k))
out=O/'PERF-SIGNAL-COMBINED.PRIVATE.patch';assert not out.exists();out.write_text(''.join(diff(base[k],combined[k],k) for k in base if base[k]!=combined[k]))
oldprofile=json.loads(prior.read_text());args=oldprofile['illustrative_command_deltas'];r=args['rust_exact_argv_source_only'][:];c=args['C_exact_argv_source_only'][:];assert r[-1]=='/src/kernel/rust/lib.rs' and c[-1]=='/src/kernel/syscall.c';assert 'f03_signal_forward_defined_candidate' not in r and '-DMCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL' not in c
r[-1:-1]=['--cfg','f03_signal_forward_defined_candidate'];c[-1:-1]=['-DMCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL']
record={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SELECTED_SOURCE_DESCRIPTION_NOT_RELEASED','inputs':{str(p):h(p) for p in exp},'combined_patch':{'path':str(out),'sha256':h(out)},'source_delta_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in combined.items() if v!=base[k]},'illustrative_raw_rust_argv':r,'illustrative_raw_C_argv':c,'link_argv_source_only':args['link_exact_argv_source_only'],'default':'Both experimental selectors absent in inherited default. Signal CMake variable tested in Linux6.12/x86_64/no-UBSAN branches, not declared by option(); unset is false. Raw profile supplies both signal flags explicitly; actual generated config and emitted args must be bound.', 'checks':['each source patch hash pinned and exact preimage applied in memory','nonoverlapping 3-way merge; identical-position insertions combined','exact signal source fa55 retained without body reimplementation','both C fallback bodies token identical to original','106 original Rust macro locations and matched unchanged nonempty C logical lines preserved; two compacted C fallback bodies retain tokens','witness objects excluded from inherited link; no held region patch lines'], 'open':['independent review of exact composite source and actual argv pairing including one-sided mismatch','actual generated config.h, include closure, SDK21 and provider identities; signal mask/action numeric real-header and Rust layout witnesses plus 2 typed signatures','actual source and link uniqueness, function pointer representation and selected getter/transport/executor consumer','matching original metadata and output object/link proof, lifetime/cancellation and functional/native behavior','fresh Root70 physical ownership/resource reconciliation and operation-specific release'], 'rebuilds':['full Rust crate rust/mckernel_rust.o','generic C kernel/CMakeFiles/mckernel.img.dir/syscall.c.o','fresh raw link after object and source rebind; nine unaffected objects only with fresh validation','separate ABI witness objects outside production link'], 'compiler_or_native_run':False,'authority':None}
f=O/'SELECTED-PROFILE.SOURCE-ONLY.json';f.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(json.dumps({'patch_sha256':h(out),'profile_sha256':h(f),'source_delta_sha256':record['source_delta_sha256']},indent=2))
