"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Validate exact real attempt2 OCI replies and original approved creation argv.
No query, guard, lock, subprocess, Docker or retirement effects.
"""
from pathlib import Path
import copy,importlib.util,json,unittest
D=Path(__file__).resolve().parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load('BFD_inherited_metadata_successor',D/'retire_exact_bfd_stopped_container.py');B=m.bindings();P,PROTECTED,PROFILE,CLAIM,PLAN,TERMINAL=m.validate_retained(B)
M=m.authenticated(B['approved_image_metadata_source'],True);ITEM=m.authenticated(M['container_reply'],True)[0];IMAGE=m.authenticated(M['image_reply'],True)[0]

def check(item=ITEM,image=IMAGE,claim=CLAIM):return m.validate_profile(item,image,B,P,PROFILE,claim,TERMINAL)

class RetainedMetadata(unittest.TestCase):
 def test_complete_real_retained_OCI_profile_is_accepted(self):
  self.assertTrue(check());self.assertEqual(ITEM['Config']['Env'],['container=oci']);self.assertEqual(ITEM['Config']['Labels'],IMAGE['Config']['Labels']);self.assertEqual(ITEM['Config']['Labels']['mckernel.owner'],'c56c894429a44fd19710ae638df0c5f3')
  self.assertNotEqual(ITEM['Config']['Labels']['mckernel.owner'],B['nonce'])
 def test_predecessor_wrong_absent_owner_assumption_reproduces(self):
  oldpath=D.parent/'uuid-api-correction-source-1/retire_exact_bfd_stopped_container.py';old=load('BFD_wrong_absent_image_label',oldpath)
  self.assertEqual(m.reference(oldpath)['sha256'],'0cabb9cdc29e9d8f90a35869b09f7eb8abf94e35ff8202a089e8fd319680afe9')
  with self.assertRaisesRegex(old.Refusal,'unchanged image labels/env'):old.validate_profile(ITEM,IMAGE,old.bindings(),P,PROFILE,CLAIM,TERMINAL)
 def test_changed_or_extra_environment_rejected_even_when_both_replies_match(self):
  for value in [['container=other'],['container=oci','UNAPPROVED=1'],[]]:
   for both in [False,True]:
    item,image=copy.deepcopy(ITEM),copy.deepcopy(IMAGE);item['Config']['Env']=value
    if both:image['Config']['Env']=copy.deepcopy(value)
    with self.subTest(env=value,both=both),self.assertRaisesRegex(m.Refusal,'exact pinned inherited image labels/env'):check(item,image)
 def test_changed_or_extra_label_rejected_even_when_both_replies_match(self):
  for key,value in [('mckernel.owner',B['nonce']),('name','other'),('UNAPPROVED','1')]:
   for both in [False,True]:
    item,image=copy.deepcopy(ITEM),copy.deepcopy(IMAGE);item['Config']['Labels'][key]=value
    if both:image['Config']['Labels'][key]=value
    with self.subTest(label=key,both=both),self.assertRaisesRegex(m.Refusal,'exact pinned inherited image labels/env'):check(item,image)
 def test_original_exact_argv_has_no_override_and_changed_argv_is_rejected(self):
  self.assertFalse(any(a in ('--env','-e','--label','-l','--env-file','--label-file') or a.startswith(('--env=','--label=')) for a in CLAIM['argv']))
  for flag in [['--env','UNAPPROVED=1'],['--label','mckernel.owner='+B['nonce']]]:
   changed=copy.deepcopy(CLAIM);index=changed['argv'].index('--entrypoint');changed['argv'][index:index]=flag
   with self.subTest(flag=flag),self.assertRaisesRegex(m.Refusal,'actual Docker claim argv unchanged'):check(claim=changed)

if __name__=='__main__':unittest.main(verbosity=2)
