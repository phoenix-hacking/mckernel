"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST ONLY controlled init bytes over genuine accepted SDK5 62-member capsule.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
D=Path(__file__).resolve().parent
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ST=load('one_init_stager',D/'stage_m05_two_generation.py')
class StageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.binding=ST.load_binding();cls.ov=load('exact_overlay',cls.binding['overlay_source']['path']);cls.old=ST.authorities(cls.binding)
  source=cls.binding['base'];raw=Path(source['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==source['sha256'] and len(raw)==source['size']
  cls.raw=cls.ov._inflate(raw,cls.binding['max_inflated_base_bytes']);cls.records=cls.ov.parse_newc(cls.raw)[0];cls.before=cls.ov._replay_records(cls.records)
  assert cls.ov._manifest(cls.before)==cls.old and len(cls.old)==62
  cls.payload=b'TEST_ONLY_NOT_A_COLLECTOR_ELF_init_successor'
  cls.b=copy.deepcopy(cls.binding);cls.b['collector']=dict(path='/TEST_ONLY/no_actual_collector',sha256=hashlib.sha256(cls.payload).hexdigest(),size=len(cls.payload),mode=0o100755)
 def test_real62base_is_actual_SDK5_producer_map(self):
  self.assertEqual(self.ov._manifest(self.before),self.old)
  for name,row in self.b['replacements'].items():self.assertEqual(self.before[name]['sha256'],row['sha256']);self.assertEqual(self.before[name]['data'],self.before[name]['data'])
 def test_one_init_rewrite_preserves61_actual_bytes_metadata_and_gzip(self):
  expected=ST.validate_selection({'init':self.b['collector']},self.old,self.b);patched=ST.rewrite_last_records(self.raw,{'init':self.payload},self.ov);after=self.ov._replay_records(self.ov.parse_newc(patched)[0]);ST.verify_delta(self.old,self.ov._manifest(after),self.b);self.assertEqual(self.ov._manifest(after),expected);self.assertEqual(after['init']['data'],self.payload)
  for n in self.old:
   if n!='init':self.assertEqual(self.before[n],after[n],n)
  self.assertEqual(self.ov._inflate(self.ov._gzip(patched),self.b['max_patched_cpio_bytes']),patched)
 def test_missing_init_refused(self):
  rows=[r for r in self.records if r['name']!='init'];raw=b''.join(self.ov._newc(r['name'],r['data'],r['mode'],ino=r['ino'])for r in rows)+self.ov._newc('TRAILER!!!',b'',0)
  with self.assertRaises(Exception):ST.rewrite_last_records(raw,{'init':self.payload},self.ov)
 def test_forbidden_duplicate_and_type_change_refused(self):
  row=next(r for r in self.records if r['name'] not in self.ov.OVERLAY_NAMES and r['name']!='.');
  with self.assertRaisesRegex(Exception,'duplicate'):self.ov._replay_records(self.records+[row])
  changed=copy.deepcopy(next(r for r in self.records if r['name']=='init'));changed['mode']=0o040755
  with self.assertRaisesRegex(Exception,'type'):self.ov._replay_records(self.records+[changed])
 def test_extra_member_and_metadata_delta_refused(self):
  final=ST.validate_selection({'init':self.b['collector']},self.old,self.b)
  for field in ('mode','uid','gid','nlink','mtime'):
   changed=copy.deepcopy(final);changed['init'][field]+=1
   with self.assertRaises(ValueError):ST.verify_delta(self.old,changed,self.b)
  changed=copy.deepcopy(final);changed['unexpected']=changed['init']
  with self.assertRaises(ValueError):ST.verify_delta(self.old,changed,self.b)
 def test_wrong_SDK_inputs_refused_without_module_rehash(self):
  for name in self.b['replacements']:
   wrong=copy.deepcopy(self.b);wrong['replacements'][name]['sha256']='0'*64
   with self.assertRaises(ValueError):ST.validate_selection({'init':wrong['collector']},self.old,wrong)
 def test_unknown_real_collector_cannot_stage(self):
  with self.assertRaises((TypeError,ValueError)):ST.validate_selection({'init':None},self.old,self.binding)
if __name__=='__main__':unittest.main(verbosity=2)
