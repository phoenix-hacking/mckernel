"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seven fixed future compiler rejection controls, executed only by Root's HOST grant.
No retry, source edit, alternate tool, dynamic command or privileged operation.
"""
from pathlib import Path
import subprocess,json,hashlib,sys,time
plan=json.loads(Path(sys.argv[1]).read_text());out=Path(plan['output']);assert out.is_dir();results=[]
for case in plan['cases']:
 prefix=out/('control-'+case['name']);stdout=Path(str(prefix)+'.stdout');stderr=Path(str(prefix)+'.stderr');assert not stdout.exists() and not stderr.exists()
 start=time.monotonic()
 with stdout.open('xb') as so,stderr.open('xb') as se:
  completed=subprocess.run(case['argv'],env=case['environment'],stdin=subprocess.DEVNULL,stdout=so,stderr=se,timeout=45,check=False)
 report=dict(name=case['name'],argv=case['argv'],environment=case['environment'],returncode=completed.returncode,seconds=time.monotonic()-start)
 for key,path in [('stdout',stdout),('stderr',stderr)]:
  assert path.stat().st_size<=64*2**20
  report[key]=dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 results.append(report);(out/'NEGATIVE-RESULTS.json').write_text(json.dumps(dict(scope=plan['scope'],results=results),indent=2)+'\n')
 assert completed.returncode!=0,case['name']+' unexpectedly compiled'
 with stderr.open('rb') as handle:diagnostic=handle.read(2**20).decode(errors='replace')
 assert case['diagnostic'] in diagnostic,(case['name'],'different compiler failure')
 assert '-o' not in case['argv'] or not Path(case['argv'][case['argv'].index('-o')+1]).exists(),case['name']+' emitted an object'
print(plan['expected_stdout'],end='')
