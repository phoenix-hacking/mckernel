"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compose private source snapshots/commands only; never invoke compiler, link or ELF reader.
"""
from pathlib import Path
import difflib
import hashlib
import json

R=Path('/home/holden/mckernel');D=Path(__file__).resolve().parent;B=D.parent
P=B/'current81-composition13-subset-qualification-preparation-1';Q=B/'new-window-source-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(p,raw):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw if isinstance(raw,bytes) else raw.encode())
def js(name,value):put(D/name,json.dumps(value,indent=2,sort_keys=True)+'\n')

overlay=json.loads((P/'CURRENT81-PRIVATE-SUPPORTED29-OVERLAY.json').read_text())
ancestor=(D/'syscall_policy.ANCESTOR.rs').read_text()
current=(R/'kernel/rust/syscall_policy.rs').read_text()
assert current==(D/'syscall_policy.CURRENT-PREIMAGE.rs').read_text()
projected=(D/'syscall_policy.SUPPORTED29-PREIMAGE.rs').read_text()
a=ancestor.splitlines(keepends=True);p=projected.splitlines(keepends=True)
merged=current;operations=[]
for kind,i,j,k,l in difflib.SequenceMatcher(None,a,p,autojunk=False).get_opcodes():
 if kind=='equal':continue
 old=''.join(a[i:j]);new=''.join(p[k:l])
 if kind=='delete':
  assert merged.count(old)==1,(kind,i,j)
  merged=merged.replace(old,'',1)
 elif kind=='insert' and i==j==len(a):
  assert merged.count(new)==0
  merged+='\n'+new
 else:raise RuntimeError(('Unexpected ancestor delta',kind,i,j,k,l))
 operations.append(dict(kind=kind,ancestor_lines=[i+1,j],private_lines=[k+1,l],old=old,new=new))
# Preserve the current root source repairs and additions, changing only six exact
# former extern declaration groups plus the independent whole-candidate additions.
fragment=(Q/'io_diagnostics.RUST-FRAGMENT.rs.inc').read_text()
assert 'mod f03_io_diagnostic_callbacks_v1' not in merged
merged+='\n'+fragment
cbase=(P/'syscall.SUPPORTED29.RUNTIME.c').read_text();c=cbase
replacements=json.loads((Q/'EXACT-GUARDED-REPLACEMENTS.json').read_text())
for row in replacements:
 assert c.count(row['original'])==1,row['symbol']
 c=c.replace(row['original'],row['replacement'],1)
source_rows=[]
for relative,row in sorted(overlay['inputs'].items()):
 actual=R/relative;raw=actual.read_bytes()
 if relative=='kernel/rust/syscall_policy.rs':raw=merged.encode()
 if relative=='kernel/rust/lib.rs':raw+=b'\n'+(P/'ABI-READONLY-WORDS.rs.inc').read_bytes()
 destination=D/'source'/relative;put(destination,raw)
 source_rows.append(dict(relative=relative,current_canonical=pin(actual),private=pin(destination)))
put(D/'source/kernel/syscall.c',c)
put(D/'source/executer/include/uti.h',(R/'executer/include/uti.h').read_bytes())
# Include actual full source and all original ABI witnesses; add the qualified
# diagnostic callbacks' exact prototypes and genuine allocated address edges.
oldabi=Path(overlay['C_ABI_aggregate']['path'])
abi=oldabi.read_text().replace(overlay['C']['private']['path'],str(D/'source/kernel/syscall.c'))
abi+='\n'+(Q/'REAL-HEADER-ABI-WITNESS.c.inc').read_text()
abi+='\n__typeof__(&syscall_swapout_log_bridge) f03_io_actual_swapout_address = &syscall_swapout_log_bridge;\n'
abi+='__typeof__(&syscall_linux_mlock_log_bridge) f03_io_actual_mlock_address = &syscall_linux_mlock_log_bridge;\n'
put(D/'source/complete62-real-ABI.c',abi)
put(D/'COHERENT-C.patch',''.join(difflib.unified_diff((R/'kernel/syscall.c').read_text().splitlines(keepends=True),c.splitlines(keepends=True),fromfile='a/kernel/syscall.c',tofile='b/kernel/syscall.c')))
put(D/'COHERENT-POLICY.patch',''.join(difflib.unified_diff(current.splitlines(keepends=True),merged.splitlines(keepends=True),fromfile='a/kernel/rust/syscall_policy.rs',tofile='b/kernel/rust/syscall_policy.rs')))
js('EXACT-ANCESTOR-DELTA-OPERATIONS.json',operations)
recipe=json.loads((P/'EXACT-CURRENT81-SUPPORTED29-CONSUMER.NOT-GRANTED.json').read_text())
commands=[]
for old in recipe['commands'][:3]:
 cmd=json.loads(json.dumps(old));cmd['cwd']=str(D);args=cmd['argv']
 for i,arg in enumerate(args):
  if str(P/'source') in arg:args[i]=arg.replace(str(P/'source'),str(D/'source'))
  elif '/current81-composition13-subset-qualification-preparation-1/source/' in arg:
   args[i]=arg.replace('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/current81-composition13-subset-qualification-preparation-1/source/',str(D/'source')+'/')
  if '/current81-composition13-subset-qualification-preparation-1/output-1/' in args[i]:
   args[i]=args[i].replace('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/current81-composition13-subset-qualification-preparation-1/output-1/',str(D/'output-proposed-1')+'/')
 if old['label'].startswith('00-'):
  at=args.index('--crate-name');args[at:at]=['--cfg','f03_io_diagnostic_callbacks_candidate']
  cmd['label']='00-current-snapshot-full-Rust-plus-io-diagnostics'
 else:
  args.insert(1,'-DMCKERNEL_RUST_F03_IO_DIAGNOSTICS')
  if old['label'].startswith('02-'):
   args=[arg.replace('complete61-real-ABI.c','complete62-real-ABI.c') for arg in args]
   cmd['label']='03-real-header62-ABI-actual-caller'
  else:cmd['label']='01-whole-selected-syscall-C'
  cmd['argv']=args
 cmd['purpose']=SCOPE+' SOURCE-ONLY proposed full candidate compilation; no grant.'
 commands.append(cmd)
fallback=json.loads(json.dumps(commands[1]));fallback['label']='02-whole-io-C-fallback-preserving-existing-subset'
fallback['argv'].remove('-DMCKERNEL_RUST_F03_IO_DIAGNOSTICS')
fallback['argv'][-1]=str(D/'output-proposed-1/F03.io-fallback.o')
commands.insert(2,fallback)
js('PROPOSED-FULLCRATE-C-TU-COMMANDS.NOT-GRANTED.json',dict(scope=SCOPE,status='SOURCE_ONLY_NO_EXECUTION_GRANT',commands=commands,tool_profile_reference=pin(P/'EXACT-CURRENT81-SUPPORTED29-CONSUMER.NOT-GRANTED.json'),compiler_grant=None,source_manifest=None,partial_link='Root must bind exact current F01/F02/F04/F05/F06 objects to this current Rust snapshot before constructing six-C partial. Do not silently reuse historical F06 object after current signal additions.',GCC14_default='Historical recipe uses qualified GCC9, not actual default GCC14 proof. Root owns required default compiler profile and linked image acceptance.'))
# Snapshot the actual include/witness dependencies without executing consumers.
header_rows=[pin(Path(row['path'])) for row in overlay['actual_header_closure']]
witness_rows=[pin(Path(row['path'])) for row in overlay['witnesses']]
js('SOURCE-COMPOSITION-HANDOFF.json',dict(scope=SCOPE,status='CURRENT_CANONICAL_PLUS_EXISTING_SUPPORTED29_PLUS_QUALIFIED_IO2_SOURCE_UNCOMPILED',base_current_C=pin(R/'kernel/syscall.c'),base_current_policy=pin(R/'kernel/rust/syscall_policy.rs'),ancestor=dict(commit='bf7f13c91d4cfa3e7d7e55689305036ac919d6c9',binding=pin(D/'syscall_policy.ANCESTOR.rs')),existing_candidate=pin(P/'CURRENT81-PRIVATE-SUPPORTED29-OVERLAY.json'),merge_resolution='Raw generic merge produced two append-block conflicts (preserved). Semantic composition instead applies only six exact extern-deletion groups and one complete EOF addition block from ancestor delta onto the full current policy; current signal/fork/perf repairs remain intact.',qualified_io=pin(Q/'ACTUAL-PARITY-EXPERT-RESULT-1.json'),preserved_prior_failures=[pin(Q/'ACTUAL-PARITY-FIRST-FAILURE-1.json'),pin(Q/'ACTUAL-PARITY-CORRECTION-FAILURE-1.json')],C=pin(D/'source/kernel/syscall.c'),policy=pin(D/'source/kernel/rust/syscall_policy.rs'),sources=source_rows,actual_headers=header_rows,existing_witnesses=witness_rows,aggregate=pin(D/'source/complete62-real-ABI.c'),C_diff=pin(D/'COHERENT-C.patch'),policy_diff=pin(D/'COHERENT-POLICY.patch'),proposed_commands=pin(D/'PROPOSED-FULLCRATE-C-TU-COMMANDS.NOT-GRANTED.json'),new_runtime_exports=[row['symbol'] for row in replacements],new_C_compute=False,existing_supported_exports_preserved=overlay['included_exports'],projection_exclusions_unchanged=overlay['excluded'],additional_excluded=['service-held fork/ACK work; no source patch or request replay'],remaining_provider_dependencies=['actual current full-crate compilation and selected/fallback whole C TUs/62 witness','current companion C object/source matching before strict partial link','original dynamic-debug flag synchronization and genuine kernel formatter qualification; controlled host output is not native proof','whole util_thread/do_syscall/do_exit/fork candidates remain separately held; no activation inferred','credential fill, exec-string ownership, UTI mapped lifetime, pending/unmap/ToFu holds unchanged','default compiler/image and exact app native smoke with normal retirement remain open'],compiler_jobs=0,execution_grant=None,canonical_edits=False,default=False,native=False,whole_file_retired=False))
print(json.dumps(pin(D/'SOURCE-COMPOSITION-HANDOFF.json')))
