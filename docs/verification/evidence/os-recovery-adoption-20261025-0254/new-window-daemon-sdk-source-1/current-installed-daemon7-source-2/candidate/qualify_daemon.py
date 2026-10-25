"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual target-header ABI, production daemon selector compile/link, loader only.
No real daemon main, devices, syslog service, mock lifecycle or guest execution.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess
BASE=Path(__file__).resolve().parent
OUT=Path('/work/daemon-sdk-1')

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 pins=json.loads((BASE/'PINNED-SDK.json').read_text())
 for key in ('cc','cmake','nm','readelf','libudev_header','libudev_library','rustc','libihk'):
  row=pins[key]
  if digest(row['path'])!=row['sha256']:raise ValueError('pinned SDK input changed: '+key)
 if digest(BASE/pins['daemon']['path'])!=pins['daemon']['sha256']:raise ValueError('latest daemon source changed')
 OUT.mkdir(mode=0o700)
 env={'PATH':'/nightly/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','MAKEFLAGS':'','CMAKE_BUILD_PARALLEL_LEVEL':'1','CARGO_BUILD_JOBS':'1','RUST_MIN_STACK':'2097152'}
 commands=[]
 def run(label,argv):
  p=subprocess.run([str(a) for a in argv],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=OUT,timeout=600,check=False)
  (OUT/(label+'.stdout')).write_bytes(p.stdout);(OUT/(label+'.stderr')).write_bytes(p.stderr)
  commands.append({'label':label,'argv':[str(a) for a in argv],'rc':p.returncode})
  (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  if p.returncode:raise RuntimeError(label+' failed; preserve first failure, no retry')
  return p.stdout.decode()
 for label,source in [('linux-ABI','linux_abi_witness.c'),('libudev-ABI','libudev_abi_witness.c')]:
  run(label,['/usr/bin/cc','-std=gnu11','-O2','-Werror','-MD','-MF',OUT/(label+'.d'),'-I/src/ihk/linux/include','-I/src/ihk/include','-c',BASE/source,'-o',OUT/(label+'.o')])
 run('selected-configure',['/usr/bin/cmake','-S',BASE/'default-selection','-B',OUT/'build','-DCMAKE_C_COMPILER:FILEPATH=/usr/bin/cc','-DIHK_USER_RUSTC:FILEPATH=/nightly/bin/rustc','-DCMAKE_INSTALL_PREFIX:PATH=/usr/local','-DCMAKE_VERBOSE_MAKEFILE:BOOL=ON'])
 run('selected-build',['/usr/bin/cmake','--build',OUT/'build','--target','ihkmond','--parallel','1'])
 binary=OUT/'build/sdk-daemon/ihkmond'
 raw=binary.read_bytes()
 if len(raw)<64 or raw[:6]!=b'\x7fELF\x02\x01' or int.from_bytes(raw[18:20],'little')!=62:raise ValueError('real Linux x86_64 daemon ELF required, never empty binary rmeta')
 dynamic=run('daemon-dynamic',['/usr/bin/readelf','-d',binary])
 for needed in ('libihk.so','libudev.so.1'):
  if not re.search(r'NEEDED.*\['+re.escape(needed)+r'\]',dynamic):raise ValueError('real daemon provider missing: '+needed)
 symbols=run('daemon-imports',['/usr/bin/nm','-D','--undefined-only',binary])
 for name in ('ihklib_device_open','ihk_os_get_eventfd'):
  if not re.search(r'\bU\s+'+name+r'(?:@|\s|$)',symbols):raise ValueError('daemon real library import missing: '+name)
 loader=run('daemon-loader',['/lib64/ld-linux-x86-64.so.2','--library-path','/accepted-libihk','--list',binary])
 if not re.search(r'libihk\.so\s+=>\s+/accepted-libihk/libihk\.so(?:\s|$)',loader):raise ValueError('loader did not select exact accepted libihk')
 result={'scope':pins['scope'],'status':'PASS_PINNED_DAEMON_ABI_SELECTED_RULE_LINK_LOADER_ONLY','commands':commands,'daemon_sha256':digest(binary),'daemon_bytes':len(raw),'pins':pins,'production_daemon_main_executed':False,'mock_parity_executed':False,'full_default_graph_or_install_accepted':False,'native_acceptance':False,'M15_file_closure':False}
 (OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
 print(result['status'])

if __name__=='__main__':
 try:main()
 except Exception as error:
  if OUT.exists():(OUT/'FAILURE.json').write_text(json.dumps({'error':str(error),'status':'FAIL_RETAINED_NO_RETRY'})+'\n')
  raise
