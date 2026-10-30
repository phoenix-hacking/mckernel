#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source proposal and synthetic mountinfo only; no mount or external process.
"""
import importlib.util,json,pathlib,unittest
p=pathlib.Path(__file__).parent
base=p.parent/'m14-root-and-nonheld-composite-1/MOUNT-MANIFEST.json'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=load('v',p/'validator.closure.py');d=load('d',p/'driver.closure.py')
class Closure(unittest.TestCase):
 def rows(self):
    source=json.loads(base.read_text())['on_source_mount_proposal'];return [('/synthetic/work','/work',False)]+[(host,target,True) for target,host in source.items()]+[('/synthetic/out','/out',True)]
 def test_exact_source_proposal_accepts_and_does_not_authorize(self):
    ref=v._check_composite_proposal(base,self.rows());self.assertEqual(ref['sha256'],v.COMPOSITE_PROPOSAL_SHA)
    with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'):v._collect({},None,None,None)
    with self.assertRaisesRegex(RuntimeError,'SOURCE_ONLY'):d.require_source_binding()
 def test_missing_changed_extra_reordered_or_writable_fails(self):
    original=self.rows()
    for what in ('missing','changed','extra','reordered','writable','missing_out'):
      rows=list(original)
      if what=='missing': rows.pop(3)
      if what=='changed': rows[3]=('/different',rows[3][1],True)
      if what=='extra': rows.insert(-1,('/extra','/src/new-extra',True))
      if what=='reordered':rows[1],rows[2]=rows[2],rows[1]
      if what=='writable':rows[-1]=(rows[-1][0],'/out',False)
      if what=='missing_out':rows.pop()
      with self.subTest(what=what),self.assertRaises(ValueError):v._check_composite_proposal(base,rows)
 def test_out_mount_and_nested_shadow(self):
    def row(n,target,opts):return f'{n} 1 0:{n} / {target} {opts},relatime - ext4 /dev/fake rw\n'
    good=(row(1,'/','rw')+row(2,'/work','rw')+row(3,'/src','ro')+row(4,'/out','ro')).encode()
    expected={'/work':False,'/src':True,'/out':True}
    self.assertEqual(d.validate_mountinfo(good,expected),4)
    for data in (good+row(5,'/out/build','rw').encode(),good+row(5,'/out/source','ro').encode(),good.replace(b'/out ro,',b'/out rw,')):
      with self.assertRaises(ValueError):d.validate_mountinfo(data,expected)
 def test_document_hash_mismatch(self):
    with self.assertRaises(ValueError):v._check_composite_proposal(p/'fake-manifest.json',self.rows())
if __name__=='__main__':unittest.main(verbosity=2)
