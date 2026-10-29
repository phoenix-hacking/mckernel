"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded EOF-module composition correction. No compiler/preprocessor/runtime work.
"""
from pathlib import Path
import json,hashlib,re,difflib
D=Path(__file__).resolve().parent;OLD=D.parent;ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists();m=json.loads((OLD/'FILEMAP.SOURCE-ONLY.json').read_text());rows={r['proposed_path']:r for r in m['files']};name='kernel/rust/syscall_policy.rs';before=(OLD/'preimage'/name).read_text();bad=(OLD/'postimage'/name).read_text()
 modules=['syscall_exit_group_current_pid','syscall_util_clone_disabled_logger','syscall_settid_logger','syscall_ptrace_clone_logger','syscall_exit_group_logger','syscall_clear_host_pte_logger'];blocks=[];stripped=bad
 for module in modules:
  pattern=r'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing\.\n(?:#\[cfg\([^\n]+\)\]\n)?#\[path = "'+module+r'\.rs"\]\nmod '+module+r';\n';hits=list(re.finditer(pattern,stripped));assert len(hits)==1,module;block=hits[0].group();blocks.append(block);stripped=stripped.replace(block,'',1)
 assert stripped==before,'all and only introduced blocks removed; entire frozen119 parent restored'
 corrected=before+''.join(blocks);assert corrected.startswith(before)
 output=[];patch=''
 for row in m['files']:
  f=row['proposed_path'];source=Path(row['postimage']['path']);assert ref(source)==row['postimage'];text=corrected if f==name else source.read_text();p=D/'postimage'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  oldtext=''
  if row['canonical_preimage']is not None:
   canonical=ROOT/f;assert ref(canonical)==row['canonical_preimage'];oldtext=(OLD/'preimage'/f).read_text();assert oldtext==canonical.read_text();q=D/'preimage'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(oldtext)
  patch+=''.join(difflib.unified_diff(oldtext.splitlines(True),text.splitlines(True),fromfile='a/'+f if row['canonical_preimage']is not None else '/dev/null',tofile='b/'+f))
  output.append(dict(proposed_path=f,postimage=ref(p),canonical_preimage=row['canonical_preimage'],reused_leaf_exact=row['reused_leaf_exact']))
 patchfile=D/'SEVEN-LEAF-LINE-PRESERVED.PRIVATE-NOT-APPLIED.patch';patchfile.write_text(patch)
 (D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_EOF_MODULE_PLACEMENT_CORRECTION_ONLY',predecessor=ref(OLD/'SOURCE-READY.json'),files=output,patch=ref(patchfile),moved_module_blocks=modules,entire_original_policy_byte_prefix_preserved=True,runtime_authority=None),indent=2)+'\n')
 (D/'ONLY-MODULE-PLACEMENT.patch').write_text(''.join(difflib.unified_diff(bad.splitlines(True),corrected.splitlines(True),fromfile=str(OLD/'postimage'/name),tofile=str(D/'postimage'/name))))
 print(json.dumps(ref(patchfile)))
if __name__=='__main__':main()
