"""Two exact create_os source slices; no full IHK/provider/native acceptance.

Rollback callback observations establish only local list lifetime/order. Real
libc owns allocator/string storage; predecessor runs two defined leaks only.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(os.environ.get("M15_REPO",Path(__file__).resolve().parents[2]))
HERE=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get("M15_CREATE_OS_SOURCE",ROOT/"ihk/linux/user/rust/whole70/ihklib_create_os_environment.rs"))
TEMPLATE=Path(os.environ.get("M15_CREATE_OS_TEMPLATE",HERE/"fixtures/m15_create_os_owned_cleanup.rs.in"))
class M15CreateOsOwnedCleanupTests(unittest.TestCase):
 def test_actual_owned_cleanup_slices(self):
  text=SOURCE.read_text();start=text.index('pub unsafe extern "C" fn ihk_create_os_str(')
  tail=text.index('    if result != 0 {\n        // Original rollback',start)
  parser_start=text.index('        if envp.is_null()',start);parser_end=text.index('        // Apply every configuration entry',parser_start)
  cleanup_start=text.index('    if !names.is_null()',parser_end)
  source=TEMPLATE.read_text().replace('__ROLLBACK__',text[tail:]).replace('__PARSER__',text[parser_start:parser_end]).replace('__ARRAY_CLEANUP__',text[cleanup_start:tail])
  with tempfile.TemporaryDirectory(prefix='m15-create-owned-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);unit=work/'witness.rs';binary=work/'witness';unit.write_text(source)
   receipt=Path(os.environ['M15_CREATE_OS_RECEIPT_DIR']) if os.environ.get('M15_CREATE_OS_RECEIPT_DIR') else None;rows=[]
   if receipt:receipt.mkdir(parents=True,exist_ok=False)
   commands=[('compile',[os.environ['RUSTC'],'--edition=2021','-Dwarnings',str(unit),'-o',str(binary)]),('witness',[str(binary)])]
   for label,argv in commands:
    result=subprocess.run(argv,capture_output=True,text=True)
    if receipt:
     rows.append({'label':label,'argv':argv,'returncode':result.returncode});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/(label+'.stdout')).write_text(result.stdout);(receipt/(label+'.stderr')).write_text(result.stderr);artifacts={}
     for artifact in [unit,binary]:
      if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);artifacts[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
     (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    self.assertEqual(result.returncode,0,repr(argv)+'\n'+result.stdout+result.stderr)
    if label=='witness':self.assertEqual(result.stdout,'baseline checks=2 expected-owned-leaks=2 reclaimed=2\n' if os.environ.get('M15_CREATE_OS_BASELINE_ONLY')=='1' else 'candidate checks=11 live-owned=0 primary-result-and-errno-order-preserved\n')
if __name__=='__main__':unittest.main()
