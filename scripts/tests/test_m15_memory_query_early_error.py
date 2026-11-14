"""Defined private reader overlength rejection; no public-query reachability claim.

Requires explicit absolute CC, RUSTC and M15_EARLY_ERROR_STAT_CFG paths. Defaults
extract current canonical C/Rust candidates and test one valid 1007-byte field
per language. Historical Rust baseline requires an explicit immutable source;
no original uninitialized-capacity C baseline, EOF or native path is run.
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
FIXTURES=HERE/'fixtures/m15-memory-early-error'
HISTORICAL_RUST_SHA256='7a29afcc122db2eb74b518f034cc9e0c660b2de9053b4cc7db65cd6c67655bfb'
HISTORICAL_UNIT_SHA256='db8de0da91fea83968e101e2387f2df0f4e89c5a980bdfc3b7a500edfc2600f4'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated selected function: '+marker)

def generate_units(c,rust_baseline,rust_candidate,observer,template):
 loglevel=re.search(r'^int loglevel = [^;]+;',c,re.M).group(0)
 observer=observer.replace('__LOGLEVEL_DECL__',loglevel)
 e_start=c.index('#define eprintf(');e_macro=c[e_start:c.index('\n\n',e_start)]+'\n'
 chk_start=c.index('#define CHKANDJUMP(');chk_macro=c[chk_start:c.index('\n\n',chk_start)]+'\n'
 debug=''.join(re.search(r'^#define '+name+r'\(fmt, args\.\.\.\) do \{  \} while \(0\)$',c,re.M).group(0)+'\n' for name in ('dnprintk','dprintf','dprintk'))
 aliases='\n#define stat(path,storage) observation_stat(path,storage)\n#define fopen(path,mode) observation_fopen(path,mode)\n#define getline(line,capacity,file) observation_getline(line,capacity,file)\n#define free(pointer) observation_free(pointer)\n#define fclose(file) observation_fclose(file)\n'
 c_path=function(c,'static int get_meminfo_path(')
 c_reader=function(c,'int ihklib_os_query_mem_sysfs(')
 if 'size_t line_len = 0;' not in c_reader:raise ValueError('Only initialized-capacity C candidate is permitted')
 units={'observer.c':observer,'c-candidate.c':observer+aliases+debug+e_macro+chk_macro+c_path+c_reader+'\nint main(int argc,char **argv){assert(argc==2);return observation_run(0,0,ihklib_os_query_mem_sysfs,argv[1]);}\n'}
 blocks={'c':{'get_meminfo_path':c_path,'reader':c_reader,'selected_DEBUG_OFF_macros':debug,'eprintf':e_macro,'CHKANDJUMP':chk_macro},'rust':{}}
 for label,source in [('rust-baseline.rs',rust_baseline),('rust-candidate.rs',rust_candidate)]:
  start=source.index('#[repr(C,align(8))]');end=source.index('unsafe extern "C"',start)
  values={'__STAT_STORAGE__':source[start:end],'__LOGGING__':function(source,'unsafe fn log<'),'__STAT_PATH__':function(source,'#[cfg(any(ihklib_stat_abi_stat,ihklib_stat_abi_xstat1))]\nunsafe fn stat_path('),'__MEM_PATH__':function(source,'unsafe fn mem_path('),'__READER__':function(source,'#[no_mangle]\npub unsafe extern "C" fn ihklib_os_query_mem_sysfs(')}
  if 'let mut line_capacity=0usize;' not in values['__READER__']:raise ValueError('Defined Rust zero-capacity reader required')
  text=template
  for marker,body in values.items():text=text.replace(marker,body)
  if re.search(r'__[A-Z_]+__',text):raise ValueError('Unresolved source marker')
  units[label]=text;blocks['rust'][label]=values
 return units,blocks


class M15MemoryQueryEarlyErrorTests(unittest.TestCase):
 def test_current_private_reader_early_cleanup(self):
  for name in ('CC','RUSTC','M15_EARLY_ERROR_STAT_CFG'):
   path=Path(os.environ[name]);self.assertTrue(path.is_absolute() and path.is_file(),name+' requires an explicit actual file')
   if name!='M15_EARLY_ERROR_STAT_CFG':self.assertTrue(os.access(path,os.X_OK),name+' requires an executable')
  stat_cfg=Path(os.environ['M15_EARLY_ERROR_STAT_CFG']).read_text().strip()
  self.assertEqual(stat_cfg,'ihklib_stat_abi_stat','Reuse the qualified actual HOST stat ABI')
  c=(ROOT/'ihk/linux/user/ihklib.c').read_text()
  baseline_path=os.environ.get('M15_EARLY_ERROR_BASELINE_SOURCE')
  if baseline_path:
   historical=Path(baseline_path);self.assertTrue(historical.is_absolute() and historical.is_file())
   self.assertEqual(hashlib.sha256(historical.read_bytes()).hexdigest(),HISTORICAL_RUST_SHA256,'Only the reviewed defined Rust baseline is allowed')
   rust=historical.read_text();languages=('rust',)
  else:
   rust=(ROOT/'ihk/linux/user/rust/whole70/ihklib_mcstat_memory_shared_parser.rs').read_text()
   languages=(os.environ['M15_EARLY_ERROR_LANGUAGE'],) if 'M15_EARLY_ERROR_LANGUAGE' in os.environ else ('c','rust')
  observer=(FIXTURES/'observations.c.in').read_text();template=(FIXTURES/'rust.rs.in').read_text()
  units,_=generate_units(c,rust,rust,observer,template)
  if baseline_path:self.assertEqual(hashlib.sha256(units['rust-baseline.rs'].encode()).hexdigest(),HISTORICAL_UNIT_SHA256,'Historical operation retains its frozen generated source')
  with tempfile.TemporaryDirectory(prefix='m15-memory-early-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);includes=['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   shared_observer=work/'observer.c';shared_observer.write_text(units['observer.c']);object_file=work/'observer.o'
   for language in languages:
    self.assertIn(language,('c','rust'));label='rust-baseline' if baseline_path else language+'-candidate'
    binary=work/label;text_directory=work/('text-'+label);text_directory.mkdir()
    if language=='c':
     unit=work/'c-candidate.c';unit.write_text(units['c-candidate.c'])
     commands=[('c-compile',[os.environ['CC'],'-std=gnu11','-Wall','-Werror',*includes,str(unit),'-o',str(binary)])];artifacts=[unit,binary]
    else:
     unit=work/(label+'.rs');unit.write_text(units[label+'.rs'])
     commands=[('observer-compile',[os.environ['CC'],'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(shared_observer),'-o',str(object_file)]),('rust-compile',[os.environ['RUSTC'],'--edition=2021','-Dwarnings','--cfg',stat_cfg,'--cfg','eof_baseline' if baseline_path else 'eof_candidate',str(unit),'-C','link-arg='+str(object_file),'-o',str(binary)])];artifacts=[unit,shared_observer,object_file,binary]
    receipt=Path(os.environ['M15_EARLY_ERROR_RECEIPT_DIR']) if 'M15_EARLY_ERROR_RECEIPT_DIR' in os.environ else work/'receipt'
    receipt=receipt/label;receipt.mkdir(parents=True,exist_ok=False);rows=[]
    commands.append(('private-early-error-run',[str(binary),str(text_directory)]))
    for phase,argv in commands:
     try:result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
     except subprocess.TimeoutExpired as error:
      (receipt/(phase+'.stdout')).write_bytes(error.stdout or b'');(receipt/(phase+'.stderr')).write_bytes(error.stderr or b'');self.fail(phase+' exceeded its bounded timeout')
     rows.append({'label':phase,'argv':argv,'returncode':result.returncode});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/(phase+'.stdout')).write_text(result.stdout);(receipt/(phase+'.stderr')).write_text(result.stderr)
     hashes={}
     for artifact in artifacts:
      if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);hashes[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
     (receipt/'artifacts.json').write_text(json.dumps(hashes,indent=2)+'\n')
     self.assertEqual(result.returncode,0,phase+'\n'+result.stdout+result.stderr);self.assertEqual(result.stderr,'',phase+' unexpected diagnostics')
     if phase=='private-early-error-run':
      self.assertEqual(result.stdout.count('GETLINE generation='),1)
      self.assertEqual(result.stdout.count('FCLOSE entry-errno=11'),1)
      self.assertIn('descriptor-closed=1',result.stdout)
      self.assertEqual(result.stdout.count('RECLAIM generation='),1 if baseline_path else 0)
      self.assertRegex(result.stdout,r'(?:baseline|candidate) queries=1 kind-bytes=1007 return=-1 output-zero-bytes=128 return-errno=\d+ line-frees='+('0 baseline-reclaims=1' if baseline_path else '1 baseline-reclaims=0')+r' file-closes=1 live=0\n$')


if __name__=='__main__':unittest.main()
