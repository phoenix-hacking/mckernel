"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source composition only; no compiler/preprocessor/payload/canonical writes.
"""
from pathlib import Path
import difflib,hashlib,json,re
D=Path(__file__).resolve().parent
A=D.parent
ROOT=Path('/home/holden/mckernel')
READY=[A/'M14-PRIVATE-SETTID-LOGGER-SUCCESSOR-1/source-successor-1/SOURCE_READY.json',A/'M14-PRIVATE-CLEAR-PTE-LOGGER-1/SOURCE_READY.json',A/'M14-PRIVATE-EXIT-GROUP-LOGGER-1/rust-metadata-successor-1/SOURCE_READY.json',A/'M14-PRIVATE-PTRACE-CLONE-LOGGER-1/source-successor-1/SOURCE_READY.json']
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(r):
 p=Path(r['path']);assert ref(p)==r,'exact input source bytes';return p

def insertion(before,after):
 start=0
 while start<min(len(before),len(after)) and before[start]==after[start]:start+=1
 suffix=0
 while suffix<len(before)-start and suffix<len(after)-start and before[-suffix-1]==after[-suffix-1]:suffix+=1
 old=before[start:len(before)-suffix if suffix else len(before)]
 add=after[start:len(after)-suffix if suffix else len(after)]
 assert not old and add,'exactly one insertion per shared source';return start,add

def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists(),'retain completed batch'
 inputs=[];maps=[];common={};leaves={}
 for ready_path in READY:
  ready=json.loads(ready_path.read_text());mapping_ref=ready.get('filemap',ready.get('files'));mapping=json.loads(auth(mapping_ref).read_text());maps.append(mapping)
  inputs.append(dict(ready=ref(ready_path),filemap=mapping_ref,leaf=ready.get('leaf',ready.get('Rust_leaf'))))
  for row in mapping['files']:
   name=row['proposed_path'];post=auth(row['postimage'])
   if row['canonical_preimage'] is None:
    assert name not in leaves;leaves[name]=post.read_text()
   else:
    old=auth(row['canonical_preimage']);assert ref(ROOT/name)==row['canonical_preimage'],'canonical still exact frozen119 preimage'
    if name in common:assert common[name]==old.read_text()
    else:common[name]=old.read_text()
 assert len(common)==3 and len(leaves)==4
 output={};construction=[]
 for name in ['kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']:
  edits=[]
  for mapping in maps:
   row=next(r for r in mapping['files'] if r['proposed_path']==name);edits.append(insertion(common[name],auth(row['postimage']).read_text()))
  assert len({position for position,_ in edits})==4
  text=common[name]
  for position,add in sorted(edits,reverse=True):text=text[:position]+add+text[position:]
  output[name]=text;construction.append(dict(path=name,operation='merge four disjoint insertions only',positions=[p for p,_ in edits]))
 c=common['kernel/syscall.c'];edits=[]
 definitions=[('settid','static void syscall_settid_log_bridge(int ret)','extern void syscall_settid_log_bridge(int ret);'),('clear','static void\nclear_host_pte_log_bridge(long error)',None),('exit','void\nexit_group_log_bridge(int pid)',None),('clone','static void\nptrace_report_clone_log_bridge(int event, int value, int result)','extern void ptrace_report_clone_log_bridge(int event, int value, int result);')]
 for label,header,declaration in definitions:
  assert c.count(header)==1;a=c.index(header);b=c.index('\n}\n',a)+2;old=c[a:b]
  if label in ('settid','clone'):new=declaration+'\n'*old.count('\n')
  else:
   # Both original bodies are five lines, with the diagnostic at offset3.
   # Keep that exact physical diagnostic line in the OFF arm; lexical tokens
   # and format bytes are unchanged. All surrounding logical origins survive.
   assert len(old.splitlines())==5
   fallback=' '.join(line.strip() for line in old.splitlines())
   declaration='extern void '+('clear_host_pte_log_bridge(long error);' if label=='clear' else 'exit_group_log_bridge(int pid);')
   new='\n'.join(['#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',declaration,'#else',fallback,'#endif'])
  assert old.count('\n')==new.count('\n'),'line-neutral replacement'
  edits.append((a,b,new));construction.append(dict(function=header,operation='line-neutral callback replacement',first_physical_line=c.count('\n',0,a)+1,source_lines=old.count('\n')+1,fallback_tokens_unchanged=label in ('clear','exit')))
 for i,(a,b,_) in enumerate(sorted(edits)):
  if i:assert sorted(edits)[i-1][1]<=a
 text=c
 for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
 assert text.count('\n')==c.count('\n');output['kernel/syscall.c']=text
 output.update(leaves)
 rows=[];patch=[]
 for name,text in output.items():
  post=D/'postimage'/name;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
  before=common.get(name,'')
  if name in common:
   pre=D/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before)
  patch.extend(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/'+name if name in common else '/dev/null',tofile='b/'+name))
  rows.append(dict(proposed_path=name,postimage=ref(post),canonical_preimage=ref(ROOT/name) if name in common else None,reused_leaf_exact=name in leaves))
 f=D/'FOUR-LOGGER-BATCH.PRIVATE-NOT-APPLIED.patch';f.write_text(''.join(patch))
 (D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope=SCOPE,status='PRIVATE_LINE_NEUTRAL_FOUR_LOGGER_BATCH_UNCOMPILED',runtime_authority=None,inputs=inputs,files=rows,patch=ref(f),construction=construction,all_original_packets_unchanged=True),indent=2)+'\n')
 print(json.dumps(ref(f)))
if __name__=='__main__':main()
