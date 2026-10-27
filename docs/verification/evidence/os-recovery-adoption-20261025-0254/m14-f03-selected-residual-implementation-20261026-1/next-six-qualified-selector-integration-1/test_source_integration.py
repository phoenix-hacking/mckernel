#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,re,unittest
P=Path(__file__).resolve().parent
S=json.loads((P/'SIX-REUSED-SELECTORS.json').read_text())
N=json.loads((P/'NEXT-THREE-COMMAND-PROFILE.NOT-GRANTED.json').read_text())
BASE=json.loads(Path(N['baseline_profile']['path']).read_text())
PRE={rel:(P/'preimage'/rel).read_text() for rel in S['base_sha256']}
POST={rel:(P/'candidate'/rel).read_text() for rel in S['base_sha256']}

def reconstructed():
 out=PRE.copy()
 for x in S['selectors']:
  d=Path(x['directory']);out['kernel/syscall.c']=out['kernel/syscall.c'].replace((d/'original.C.inc').read_text(),(d/'paired-selector.C.inc').read_text(),1)
  raw=(d/'reused-original.Rust.inc').read_text();frag=(d/'selected.Rust.inc').read_text()
  if raw:out['kernel/rust/syscall_policy.rs']=out['kernel/rust/syscall_policy.rs'].replace(raw,frag,1)
  elif frag:out['kernel/rust/syscall_policy.rs']+='\n'+frag
 cm=out['kernel/CMakeLists.txt'];old='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_wait_release_selected_candidate")\n';add=''.join('\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+x+'")\n' for x in S['new_Rust_cfgs']);cm=cm.replace(old,old+add,1)
 old='MCKERNEL_RUST_F03_MMAP_PAGE_CALLBACK;MCKERNEL_RUST_F03_WAIT_RELEASE")';cm=cm.replace(old,old[:-2]+';'+';'.join(S['new_C_defines'])+'")',1);out['kernel/CMakeLists.txt']=cm
 return out

def scopes_for_tokens(text,tokens):
 stack=[];found={}
 for line in text.splitlines():
  m=re.match(r'\s*if\s*\((.*)\)\s*(?:#.*)?$',line)
  if m:stack.append(m.group(1))
  elif re.match(r'\s*endif\b',line):
   if stack:stack.pop()
  for token in tokens:
   if token in line:found[token]=stack.copy()
 return found

class Integration(unittest.TestCase):
 def test_exact_Root_base_pins(self):
  for rel,sha in S['base_sha256'].items():self.assertEqual(hashlib.sha256((P/'preimage'/rel).read_bytes()).hexdigest(),sha)
 def test_only_three_private_source_files_and_exact_changes(self):
  self.assertEqual({str(p.relative_to(P/'candidate')) for p in (P/'candidate').rglob('*') if p.is_file()},set(PRE))
  self.assertEqual(reconstructed(),POST)
 def test_six_C_regions_original_fallback_and_no_duplicate_selection(self):
  self.assertEqual(len(S['selectors']),6)
  for x in S['selectors']:
   d=Path(x['directory']);old=(d/'original.C.inc').read_text();sel=(d/'paired-selector.C.inc').read_text()
   self.assertEqual(PRE['kernel/syscall.c'].count(old),1);self.assertEqual(POST['kernel/syscall.c'].count(sel),1);self.assertTrue(sel.endswith('#else\n'+old+'#endif\n'))
 def test_four_Rust_exports_body_reuse_and_existing_aliases(self):
  rs=POST['kernel/rust/syscall_policy.rs']
  for name in ['f03_wait_release_process','f03_terminate_host_refcount_set_v1','f03_ptrace_io_find','f03_ptrace_io_unlock','syscall_copy_from_user_bridge']:
   self.assertEqual(len(re.findall(r'\bfn '+name+r'\(',rs)),1,name)
  self.assertEqual(rs.count('mod f03_terminate_refcount_selected {'),1)
  for x in S['selectors']:
   d=Path(x['directory']);frag=(d/'selected.Rust.inc').read_text()
   if frag:self.assertIn(frag,rs)
   elif x['number']==3:self.assertIsNone(x['cfg'])
 def test_four_cfgs_six_defines_with_same_supported_gate(self):
  self.assertEqual(len(S['new_Rust_cfgs']),4);self.assertEqual(len(S['new_C_defines']),6)
  text=POST['kernel/CMakeLists.txt'];found=scopes_for_tokens(text,S['new_Rust_cfgs']+S['new_C_defines'])
  for token in S['new_Rust_cfgs']+S['new_C_defines']:
   self.assertEqual(text.count(token),1)
   self.assertIn('MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12"',found[token]);self.assertIn('ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN',found[token])
 def test_prior_cohort_and_F06_CMake_tokens_preserved(self):
  for token in re.findall(r'MCKERNEL_RUST_F06_[A-Z_]+|f06_[a-z0-9_]+',PRE['kernel/CMakeLists.txt']):
   self.assertEqual(PRE['kernel/CMakeLists.txt'].count(token),POST['kernel/CMakeLists.txt'].count(token))
  for cfg in ['f03_prlimit_body_candidate','f03_do_exit_supported_candidate','f03_unmap_begin_selected_candidate','f03_unmap_remove_selected_candidate','f03_unmap_finish_selected_candidate','f03_mmap_page_callback_candidate','f03_wait_release_selected_candidate']:
   self.assertEqual(PRE['kernel/CMakeLists.txt'].count(cfg),POST['kernel/CMakeLists.txt'].count(cfg))
 def test_exact_three_argv_deltas_no_x86_or_process_replay(self):
  cs=N['exact_commands'];self.assertEqual(len(cs),3)
  a=cs[0]['argv'].copy()
  for cfg in S['new_Rust_cfgs']:
   i=a.index(cfg);self.assertEqual(a[i-1],'--cfg');del a[i-1:i+1]
  self.assertEqual(a,BASE['exact_commands'][0]['argv'])
  a=[v for v in cs[1]['argv'] if v not in ['-D'+x for x in S['new_C_defines']]];self.assertEqual(a,BASE['exact_commands'][1]['argv'])
  self.assertEqual(cs[2]['argv'],BASE['exact_commands'][3]['argv']);self.assertNotIn(BASE['exact_commands'][2]['argv'],[x['argv'] for x in cs])
  self.assertEqual(N['reuse_requirement']['status'],'PENDING_ROOT_ARTIFACT_ACCEPTANCE_BINDING')
  for c in cs:self.assertEqual(hashlib.sha256((json.dumps(c['argv'],separators=(',',':'))+'\n').encode()).hexdigest(),c['argv_compact_json_LF_sha256'])
 def test_no_runtime_authority_and_existing_profile_unchanged(self):
  self.assertIsNone(N['runtime_authority']);self.assertIsNone(N['request_sha256']);self.assertFalse(N['compiler_execution'])
  b=N['baseline_profile'];raw=Path(b['path']).read_bytes();self.assertEqual(len(raw),b['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),b['sha256'])
  for key in ['CPU','memory_bytes','pids','maximum_wall_seconds','deadline_epoch','docker_client_prefix']:self.assertEqual(N[key],BASE[key])

if __name__=='__main__':unittest.main(verbosity=2)
