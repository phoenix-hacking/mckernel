"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual parser/snapshot bodies; raw captured device fields, synthetic other metadata.
"""
import importlib.util,json,os,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('candidate3_existing_tests',D/'test_grow_scratch.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old);g=old.g
class ExpertParserTests(unittest.TestCase):
 def test_actual_raw_fields_decode(self):
  row=json.loads((D/'ACTUAL-LOSETUP1.raw.json').read_text())['loopdevices'][0]
  self.assertEqual(g.parse_major_minor(row['maj:min']),(7,36));self.assertEqual(g.parse_major_minor(row['back-maj:min']),(259,2))
 def test_decimal_padding_and_bound(self):
  for text,result in [('7:36',(7,36)),('  7:36 ',(7,36)),('\t007:00036\t',(7,36)),('0:0',(0,0)),(' '*60+'1:2 ',(1,2))]:
   with self.subTest(text=text):self.assertEqual(g.parse_major_minor(text),result)
 def test_malformed_rejected(self):
  for value in [None,True,7,b'7:36',[],{},'',':','7','7:','7:36:1','7 :36','7: 36','+7:36','-7:36','0x7:36','7:0x24','７:36','7:٣٦','\u00a07:36','7:36\n','\n7:36','\r7:36','7:36\v','7:36\f',' '*61+'1:2 ','1:2\x00']:
   with self.subTest(value=repr(value)):
    with self.assertRaises(g.Stop):g.parse_major_minor(value)
 def snapshot_with_actual_fields(self,changes=None):
  with old.StorageFixture() as fixture:
   fixture.device='/dev/loop36';fixture.devnum=os.makedev(7,36);fixture.mount_dev=fixture.devnum
   original=fixture.run
   def observed(argv,timeout=20):
    if argv[0]=='/usr/sbin/losetup' and '--list'in argv:
     row=json.loads((D/'ACTUAL-LOSETUP1.raw.json').read_text())['loopdevices'][0]
     # Only path/identity fixture bindings differ; padded raw device fields stay exact.
     row.update(name=fixture.device,**{'back-file':str(fixture.backing),'back-ino':fixture.back_ino})
     if changes:row.update(changes)
     return json.dumps({'loopdevices':[row]}),''
    return original(argv,timeout)
   return g.snapshot(observed,(g.OLD,g.OLD,g.OLD_BLOCKS))
 def test_actual_fields_snapshot_passes_synthetic_header(self):
  result=self.snapshot_with_actual_fields();self.assertEqual(result['devnum'],os.makedev(7,36))
 def test_wrong_loop_device_rejected(self):
  with self.assertRaises(g.Stop):self.snapshot_with_actual_fields({'maj:min':' 7:35 '})
 def test_wrong_backing_device_rejected(self):
  with self.assertRaises(g.Stop):self.snapshot_with_actual_fields({'back-maj:min':' 259:3 '})
 def test_backing_inode_gate_unchanged(self):
  with self.assertRaises(g.Stop):self.snapshot_with_actual_fields({'back-ino':47468428})
if __name__=='__main__':unittest.main()
