"""Two defined C creation empty-entry ownership cases using real libc.

Requires an explicit absolute CC. Default extracts current canonical C only.
Historical all-success allocation baseline requires explicit defined-baseline mode
and the pinned immutable C source. No failed-duplicate, Rust or native path runs.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_m15_create_entry_allocations import generate_c_unit

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURE=HERE/'fixtures/m15-create-empty-entry/observations.c.in'
BASELINE_SOURCE_SHA256='57a1272103bbc3b0f6c27c1d08b93aa4fe2eb7c3467e4e5d7c3eb0aa72499134'
BASELINE_UNIT_SHA256='75d4b2dc1a3ed14398e53d2a4d9707d3cb0d27d2a236a9efbabd30c1a75ac1b4'


def expected_output(baseline):
 return ''.join(f'CASE empty-entry={entry} baseline={int(baseline)} result=-22 index=12345 allocated={3+3*(entry-1)} freed={3+3*(entry-1)} retained-before-reclaim={int(baseline)} local-errno-restored={int(not baseline)}\n' for entry in (1,2))+'creation empty-entry cases=2 all-libc-allocations-successful final-live=0\n'


class M15CreateEmptyEntryTests(unittest.TestCase):
 def test_c_empty_entry_ownership(self):
  cc=Path(os.environ['CC']);self.assertTrue(cc.is_absolute() and cc.is_file() and os.access(cc,os.X_OK),'CC requires an explicit absolute executable')
  mode=os.environ.get('M15_CREATE_EMPTY_MODE','candidate');self.assertIn(mode,('candidate','defined-baseline'))
  baseline=mode=='defined-baseline';historical=os.environ.get('M15_CREATE_EMPTY_BASELINE_SOURCE')
  if baseline:
   self.assertTrue(historical,'defined-baseline requires explicit immutable source')
   source=Path(historical);self.assertTrue(source.is_absolute() and source.is_file())
   self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),BASELINE_SOURCE_SHA256,'Only the reviewed successful-allocation baseline is allowed')
  else:
   self.assertIsNone(historical,'Baseline source also requires explicit defined-baseline mode')
   source=ROOT/'ihk/linux/user/ihklib.c'
  unit,_=generate_c_unit(source.read_text(),FIXTURE.read_text())
  if baseline:self.assertEqual(hashlib.sha256(unit.encode()).hexdigest(),BASELINE_UNIT_SHA256,'Historical extraction retains the exact reviewed baseline')
  with tempfile.TemporaryDirectory(prefix='m15-create-empty-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);c_file=work/'empty.c';binary=work/'empty';c_file.write_text(unit)
   compile_argv=[str(cc),'-std=gnu11','-Wall','-Werror','-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   if baseline:compile_argv.append('-DEMPTY_BASELINE')
   compile_argv.extend([str(c_file),'-o',str(binary)])
   receipt=Path(os.environ['M15_CREATE_EMPTY_RECEIPT_DIR']) if 'M15_CREATE_EMPTY_RECEIPT_DIR' in os.environ else None
   if receipt:receipt.mkdir(parents=True,exist_ok=False)
   rows=[]
   for label,argv in [('compile',compile_argv),('run',[str(binary)])]:
    result=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
    rows.append({'label':label,'argv':argv,'returncode':result.returncode,'direct_wait_joined':True})
    if receipt:
     (receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/(label+'.stdout')).write_text(result.stdout);(receipt/(label+'.stderr')).write_text(result.stderr)
     artifacts={}
     for path in (c_file,binary):
      if path.is_file():shutil.copyfile(path,receipt/path.name);artifacts[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
     (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    self.assertEqual(result.returncode,0,label+'\n'+result.stdout+result.stderr);self.assertEqual(result.stderr,'',label+' unexpected diagnostics')
    self.assertEqual(result.stdout,expected_output(baseline) if label=='run' else '')


if __name__=='__main__':unittest.main()
