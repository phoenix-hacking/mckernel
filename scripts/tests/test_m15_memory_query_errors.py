"""Actual total/free memory queries with deterministic ordinary allocation errors.

All records are valid. The sysfs/open boundary is explicitly observed; successful
storage/string/anonymous-descriptor operations reach genuine HOST libc. No IHK
sysfs/device/native behavior or later invalid-node transaction is claimed.
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
FIXTURES=HERE/'fixtures/m15-memory-query-errors'


def function(source, marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual function: '+marker)


class M15MemoryQueryErrorTests(unittest.TestCase):
 def test_actual_public_queries(self):
  baseline=os.environ.get('M15_MEMORY_ERROR_BASELINE_ONLY')=='1'
  languages=(os.environ['M15_MEMORY_ERROR_LANGUAGE'],) if 'M15_MEMORY_ERROR_LANGUAGE' in os.environ else ('c','rust')
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler])
   self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  for language in languages:
   self.check_language(language,baseline,len(languages)>1)

 def check_language(self,language,baseline,both):
  if baseline:
   c_source=Path(os.environ['M15_MEMORY_ERROR_C_SOURCE']);rust_source=Path(os.environ['M15_MEMORY_ERROR_RUST_SOURCE']);parser_source=Path(os.environ['M15_MEMORY_ERROR_PARSER_SOURCE'])
  else:
   c_source=ROOT/'ihk/linux/user/ihklib.c';rust_source=ROOT/'ihk/linux/user/rust/whole70/ihklib_mcstat_memory_shared_parser.rs';parser_source=ROOT/'ihk/linux/user/rust/whole70/ihklib_cli_parsers_ikc_shared.rs'
  c=c_source.read_text();rust=rust_source.read_text();parser=parser_source.read_text();observer=Path(os.environ.get('M15_MEMORY_ERROR_OBSERVER',FIXTURES/'observations.c.in')).read_text();template=Path(os.environ.get('M15_MEMORY_ERROR_RUST_TEMPLATE',FIXTURES/'rust.rs.in')).read_text()
  loglevel=re.search(r'^int loglevel = [^;]+;',c,re.M).group(0);observer=observer.replace('__LOGLEVEL_DECL__',loglevel)
  with tempfile.TemporaryDirectory(prefix='m15-memory-errors-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);binary=work/'memory-errors';cc=os.environ['CC'];includes=['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   if language=='c':
    chunks=function(c,'static int mem_str2chunks(');query=function(c,'static int ihklib_os_query_mem(');assert re.search(r'memset\(mem_chunks,\s*0,\s*sizeof\(mem_chunks\)\)',query),'C failure baseline requires actual zero initialization'
    macro_start=c.index('#define CHKANDJUMP(');macro=c[macro_start:c.index('\n\n',macro_start)]+'\n';error_start=c.index('#define eprintf(');error_macro=c[error_start:c.index('\n\n',error_start)]+'\n';all_macro=re.search(r'^#define IHK_SMP_MEM_ALL[^\n]+',c,re.M).group(0)+'\n';kinds=re.search(r'const char \*ihklib_os_query_mem_type_str\[\]\s*=\s*\{.*?\n\};',c,re.S).group(0)+'\n'
    aliases='\n#define dprintf(...) ((void)0)\n#define dprintk(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('calloc','observation_calloc'),('strdup','observation_strdup'),('free','observation_free'),('close','observation_close'),('ihklib_os_open','observation_open'),('ihklib_os_query_mem_sysfs','observation_sysfs')])
    bodies=''.join(function(c,marker) for marker in ['static long ihk_memparse(','static int mem_str2array(','int mem_str2count('])+chunks+query+function(c,'int ihk_os_query_total_mem(')+function(c,'int ihk_os_query_free_mem(')
    unit=work/'memory-errors.c';unit.write_text(observer+aliases+error_macro+macro+all_macro+kinds+bodies+'\nint main(void){return observation_run('+str(int(baseline))+',ihk_os_query_total_mem,ihk_os_query_free_mem);}\n');artifacts=[unit,binary];commands=[('c-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(unit),'-o',str(binary)])]
   elif language=='rust':
    parser_functions=function(parser,'unsafe fn is(')+function(parser,'unsafe fn mem_parse(')+function(parser,'pub(super) unsafe fn mem_array(')
    chunk_start=rust.index('#[repr(C)]');chunk_end=rust.index('// stat fields',chunk_start);chunk_type=rust[chunk_start:chunk_end]
    log_start=rust.index('unsafe fn log<');log_end=rust.index('#[cfg(not(any(',log_start);logging=rust[log_start:log_end]
    query_start=rust.index('unsafe fn mem_chunks(');query_end=rust.index('#[cfg(ihklib_mcstat_fixture)]',query_start);query=rust[query_start:query_end]
    unit=work/'memory-errors.rs';unit.write_text(template.replace('__PARSER__',parser_functions).replace('__MEM_CHUNK_TYPE__',chunk_type).replace('__LOGGING__',logging).replace('__QUERY_AND_PUBLIC_WRAPPERS__',query));observation_source=work/'observations.c';observation_source.write_text(observer);object_file=work/'observations.o';artifacts=[unit,observation_source,object_file,binary];commands=[('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(observation_source),'-o',str(object_file)]),('rust-compile',[os.environ['RUSTC'],'--edition=2021','-Dwarnings',str(unit),'-C','link-arg='+str(object_file),'-o',str(binary)])]
   else:self.fail('Explicit c or rust required')
   receipt=Path(os.environ['M15_MEMORY_ERROR_RECEIPT_DIR']) if 'M15_MEMORY_ERROR_RECEIPT_DIR' in os.environ else work/'receipt'
   if both:receipt=receipt/language
   receipt.mkdir(parents=True,exist_ok=False);rows=[];commands.append(('memory-query-run',[str(binary)]))
   for label,argv in commands:
    result=subprocess.run(argv,capture_output=True,text=True);rows.append({'label':label,'argv':argv,'returncode':result.returncode});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/(label+'.stdout')).write_text(result.stdout);(receipt/(label+'.stderr')).write_text(result.stderr);hashes={}
    for artifact in artifacts:
     if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);hashes[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    (receipt/'artifacts.json').write_text(json.dumps(hashes,indent=2)+'\n');self.assertEqual(result.returncode,0,repr(argv)+'\n'+result.stdout+result.stderr)
    if label=='memory-query-run':self.assertEqual(result.stdout,'baseline checks=14 defined-false-successes=8 all-owned-fds-once-closed all-blocks-freed\n' if baseline else 'candidate checks=14 allocation-errors-propagated converter-error-outputs-unchanged all-owned-fds-once-closed all-blocks-freed\n')
if __name__=='__main__':unittest.main()
