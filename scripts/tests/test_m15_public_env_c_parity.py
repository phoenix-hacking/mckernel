"""Current C parse_env allocation rollback, with thirteen defined parser cases.

Requires explicit absolute CC. The default extracts the current canonical public
parser; no Rust compiler, creation parser or device provider is used. Historical
baseline mode requires both M15_PUBLIC_ENV_BASELINE=1 and an immutable source path.
Baseline NULL slots are compared as pointers and never dereferenced.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
OBSERVER=HERE/'fixtures/m15-public-env-parity/observer.c.in'
HISTORICAL_C_SHA256='57a1272103bbc3b0f6c27c1d08b93aa4fe2eb7c3467e4e5d7c3eb0aa72499134'
HISTORICAL_UNIT_SHA256='d728df443688fca3cd84691c42f18688eba8080abc790cd5654de471625bb746'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated selected function: '+marker)


def generate_unit(source,observer,baseline):
 parser=function(source,'int parse_env(')
 macro=re.search(r'^#define dprintf\(fmt, args\.\.\.\) do \{  \} while \(0\)$',source,re.M).group(0)+'\n'
 return observer.replace('__SELECTED_DPRINTF__',macro).replace('__SELECTED_PARSE_ENV__',parser).replace('__BASELINE__',str(int(baseline)))


class M15PublicEnvironmentCParityTests(unittest.TestCase):
 def test_current_C_parser_rollback(self):
  cc=Path(os.environ['CC']);self.assertTrue(cc.is_absolute() and cc.is_file() and os.access(cc,os.X_OK),'CC must be an explicit actual executable')
  mode=os.environ.get('M15_PUBLIC_ENV_BASELINE','0');self.assertIn(mode,('0','1'))
  historical=os.environ.get('M15_PUBLIC_ENV_BASELINE_SOURCE');baseline=mode=='1'
  if baseline:
   self.assertTrue(historical,'Baseline mode requires an explicit immutable source')
   source_path=Path(historical);self.assertTrue(source_path.is_absolute() and source_path.is_file())
  else:
   self.assertFalse(historical,'An explicit baseline source also requires baseline mode')
   source_path=ROOT/'ihk/linux/user/ihklib.c'
  source_raw=source_path.read_bytes();source=source_raw.decode()
  if baseline:self.assertEqual(hashlib.sha256(source_raw).hexdigest(),HISTORICAL_C_SHA256,'Only the reviewed defined C baseline is allowed')
  unit=generate_unit(source,OBSERVER.read_text(),baseline)
  if baseline:self.assertEqual(hashlib.sha256(unit.encode()).hexdigest(),HISTORICAL_UNIT_SHA256,'Historical operation keeps its qualified generated source')
  with tempfile.TemporaryDirectory(prefix='m15-public-env-c-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);c=work/'parser.c';binary=work/'parser';c.write_text(unit)
   receipt=Path(os.environ['M15_PUBLIC_ENV_RECEIPT_DIR']) if 'M15_PUBLIC_ENV_RECEIPT_DIR' in os.environ else work/'receipt'
   receipt.mkdir(parents=True,exist_ok=False);rows=[]
   (receipt/'source.json').write_text(json.dumps({'path':str(source_path),'source_sha256':hashlib.sha256(source_raw).hexdigest(),'parse_env_sha256':hashlib.sha256(function(source,'int parse_env(').encode()).hexdigest(),'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'baseline':baseline},indent=2)+'\n')
   includes=['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   commands=[('compile',[str(cc),'-std=gnu11','-Wall','-Werror',*includes,str(c),'-o',str(binary),'-Wl,--wrap=calloc','-Wl,--wrap=strndup','-Wl,--wrap=strdup','-Wl,--wrap=free']),('parser-run',[str(binary)])]
   for label,argv in commands:
    try:result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
    except subprocess.TimeoutExpired as error:
     (receipt/(label+'.stdout')).write_bytes(error.stdout or b'');(receipt/(label+'.stderr')).write_bytes(error.stderr or b'');self.fail(label+' exceeded its bounded timeout')
    rows.append({'label':label,'argv':argv,'returncode':result.returncode});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/(label+'.stdout')).write_text(result.stdout);(receipt/(label+'.stderr')).write_text(result.stderr)
    artifacts={}
    for artifact in [c,binary]:
     if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);artifacts[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    self.assertEqual(result.returncode,0,label+'\n'+result.stdout+result.stderr);self.assertEqual(result.stderr,'',label+' unexpected diagnostics')
    if label=='parser-run':self.assertTrue(result.stdout.endswith('baseline checks=13 false-successes=6 retained-error-owners=4 reclaimed=38 live=0\n' if baseline else 'candidate checks=13 false-successes=0 retained-error-owners=0 reclaimed=0 live=0\n'))


if __name__=='__main__':unittest.main()
