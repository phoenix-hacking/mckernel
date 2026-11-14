"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two-command original-C/original-C diagnostic only, not Rust/SDK21 acceptance.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parents[1]
PREFIX=Path('/prefix')
OUT=Path('/work/cc-repeat-control-1')
PREFIX_FILES={'mcinspect-original-renamed.o': {'bytes': 1504, 'sha256': 'a180e46408c79d35f7482d5c4cfb510f46a5a892ab18ba1b39de4b067e8cf4a6'}, 'eclair-original-renamed.o': {'bytes': 1496, 'sha256': '8cb0d3cea9ded4c2798317061ca93e76569a0b0ab9ab3c95b9111899b20b408b'}, 'fixture.o': {'bytes': 3128, 'sha256': 'a6176c3bc554b55a593056cf41737cc22d95aa76d2de28cd1db4a5663bc26a88'}, 'stripped.o': {'bytes': 896, 'sha256': '029e97d0340e8b35b3c92f6bdf06dd14b924de62aa169ab8bc3297234ee30495'}, 'bfd_layout.rs': {'bytes': 259, 'sha256': 'e21b4d9975984b7c14e13760c232dda4e755c5955f1649df77ebdc38e065530b'}}
CONTROL_COMMANDS=[['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '/candidate/tests/original_C_twice_pinned_BFD_control.c', '/prefix/mcinspect-original-renamed.o', '/prefix/eclair-original-renamed.o', '/usr/lib64/libbfd.so', '-o', '/work/cc-repeat-control-1/original-c-twice'], ['/work/cc-repeat-control-1/original-c-twice', '/prefix/fixture.o', '/prefix/stripped.o']]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 assert sys.argv[1:]==['--control-once']
 pins=json.loads((BASE/'PINNED-ABI.json').read_bytes())
 for name in ['header','library','cc','rustc']:
  row=pins[name];assert digest(Path(row['path']))==row['sha256'], 'same pinned tool/header/library required'
 for name,row in PREFIX_FILES.items():
  path=PREFIX/name;assert path.stat().st_size==row['bytes'] and digest(path)==row['sha256'], 'retained successful prefix drift'
 for name,sha in json.loads((BASE/'SOURCE-BINDING.json').read_bytes())['sources'].items():assert digest(Path('/src')/name)==sha
 assert not OUT.exists();OUT.mkdir(mode=0o700);(OUT/'tmp').mkdir(mode=0o700)
 env={'PATH':'/nightly/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','MAKEFLAGS':'','CMAKE_BUILD_PARALLEL_LEVEL':'1','CARGO_BUILD_JOBS':'1','TMPDIR':str(OUT/'tmp')};commands=[]
 def run(argv,name):
  proc=subprocess.run(argv,cwd=OUT,env=env,capture_output=True,timeout=30)
  (OUT/(name+'.stdout')).write_bytes(proc.stdout);(OUT/(name+'.stderr')).write_bytes(proc.stderr)
  commands.append(dict(argv=argv,cwd=str(OUT),rc=proc.returncode,log=name))
  (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  if proc.returncode!=0:raise RuntimeError(name+': rc '+str(proc.returncode)+'; see retained log')
  return proc
 try:
  run(CONTROL_COMMANDS[0],'original-c-twice-link');proc=run(CONTROL_COMMANDS[1],'original-c-twice-run')
  assert proc.stderr==b'' and proc.stdout.endswith(b'PASS ORIGINAL_C_TWICE_CONTROL_ONLY_NO_RUST_ABI_ACCEPTANCE\n')
  rows=[]
  for line in proc.stdout.decode('utf-8').splitlines():
   if line.startswith('POINTER_IDENTITY '):
    _,label,count,changed=line.split();rows.append(dict(wrapper=label,count=int(count),changed=int(changed)))
  assert len(rows)==2 and [x['wrapper'] for x in rows]==['mcinspect','eclair'] and all(x['count']>0 and 0<=x['changed']<=x['count'] for x in rows)
  result=dict(schema='mckernel.bfd.original-c-twice.control-result.v1',status='PASS_ORIGINAL_C_TWICE_CONTROL',scope=__doc__.splitlines()[0],commands=commands,retained_prefix=PREFIX_FILES,pointer_identity=rows,any_pointer_changed=any(x['changed']>0 for x in rows),symbol_metadata_preserved=True,Rust_ABI_acceptance=False,SDK21_acceptance=False,native_acceptance=False,M15_file_closure=False)
  (OUT/'RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
 except Exception as error:
  (OUT/'FAILURE.json').write_text(json.dumps(dict(status='FAIL_RETAINED_NO_RETRY',error=str(error),Rust_ABI_acceptance=False))+'\n');raise
if __name__=='__main__':main()
