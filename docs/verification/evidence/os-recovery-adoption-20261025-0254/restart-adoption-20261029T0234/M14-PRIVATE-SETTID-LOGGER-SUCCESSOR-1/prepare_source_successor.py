"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source construction only; no compiler, payload, controller or canonical writes.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 dest=D/'source-successor-1';assert not dest.exists();dest.mkdir()
 leaf=(D/'DRAFT.syscall_settid_logger.rs').read_text().replace('//! DRAFT ONLY: same-name successor for existing settid warning callback.','//! Private uncompiled successor for the existing settid warning callback.')
 outputs={'kernel/rust/syscall_settid_logger.rs':leaf}
 name='kernel/syscall.c';old=(ROOT/name).read_text();anchor='''static void syscall_settid_log_bridge(int ret)
{
\tkprintf("settid: WARNING: do_syscall returns %d\\n", ret);
}''';assert old.count(anchor)==1,'one exact C bridge';outputs[name]=old.replace(anchor,'extern void syscall_settid_log_bridge(int ret);')
 name='kernel/rust/syscall_policy.rs';old=(ROOT/name).read_text();anchor='use core::ffi::c_void;\n'
 # The old substring occurs in nested test modules too. Bind only the exact file
 # prefix; a changed prefix refuses instead of replacing any nested occurrence.
 assert old.startswith(anchor),'exact leading production import'
 insert='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[path = "syscall_settid_logger.rs"]\nmod syscall_settid_logger;\n'
 outputs[name]=anchor+insert+old[len(anchor):]
 name='kernel/CMakeLists.txt';old=(ROOT/name).read_text();anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert old.count(anchor)==1,'one explicit production Rust dependency';outputs[name]=old.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_settid_logger.rs"\n')
 patch=[];rows=[]
 for name,text in outputs.items():
  post=dest/'postimage'/name;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text);current=ROOT/name;before=current.read_text() if current.exists() else ''
  if current.exists():
   pre=dest/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before)
  patch.extend(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/'+name if current.exists() else '/dev/null',tofile='b/'+name))
  rows.append(dict(proposed_path=name,postimage=ref(post),canonical_preimage=ref(current) if current.exists() else None))
 f=dest/'SETTID-LOGGER.PRIVATE-NOT-APPLIED.patch';f.write_text(''.join(patch))
 (dest/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope=SCOPE,status='PRIVATE_SETTID_SOURCE_SUCCESSOR_UNCOMPILED',runtime_authority=None,files=rows,patch=ref(f),retained_draft=ref(D/'DRAFT.syscall_settid_logger.rs'),retained_checkpoint=ref(D/'MODEL-ONLY-CHECKPOINT.json'),parent_abi=ref(ROOT/'kernel/rust/abi.rs'),parent_lib=ref(ROOT/'kernel/rust/lib.rs')),indent=2)+'\n')
 print(json.dumps(ref(f)))
if __name__=='__main__':main()
