from pathlib import Path
import hashlib,json,re,subprocess
repo=Path('/workspace');out=Path('/work/spark-goal-docs-check-20260909-1');out.mkdir()
record={'status':'RUNNING','scope':'Documentation references and preservation checks; no fixture or runtime execution'}
try:
 subprocess.run(['git','-C',str(repo),'diff','--check'],check=True)
 checked=[]
 for name in ['codex-spark-goal-20260909.md','codex-spark-runbook-20260909.md']:
  p=repo/'docs/verification'/name;s=p.read_text()
  for target in re.findall(r'\]\(([^)]+)\)',s):
   q=(p.parent/target.split('#')[0]).resolve();assert q.is_file(),(name,target);checked.append(str(q.relative_to(repo)))
  for target in re.findall(r'`((?:docs/verification|scripts/application-tests)/[^`]+)`',s):
   if target.endswith('/') or '*' in target:continue
   assert (repo/target).is_file(),target
   checked.append(target)
  assert p.read_bytes().endswith(b'\n') and not p.read_bytes().endswith(b'\n\n')
 goal=(repo/'docs/verification/codex-spark-goal-20260909.md').read_text().split('## Goal to paste into Goal mode\n\n',1)[1].split('\n## Entry files',1)[0]
 assert goal in (repo/'goal.txt').read_text().split('END ACTIVE SPARK GOAL',1)[0]
 release=json.loads((repo/'docs/verification/ultra-drafting-handoff-20260909.json').read_text())
 preserved=['docs/verification/ultra-drafting-handoff-20260909.json','scripts/application-tests/README.md','scripts/application-tests/handoff-start.md','scripts/application-tests/validate.py']
 preserved.extend(row['path'] for row in release.values() if isinstance(row,dict) and {'path','size','sha256'}<=row.keys() and not row['path'].startswith('/'))
 preserved.extend(str(p.relative_to(repo)) for p in (repo/'scripts/application-tests/packets').glob('*.json'))
 for target in set(preserved):
  assert (repo/target).read_bytes()==subprocess.check_output(['git','-C',str(repo),'show','7b322981:'+target]),target
 proof=json.loads((repo/'docs/verification/evidence/ultra-handoff-github-verification-20260909-1.json').read_text())
 assert proof['status']=='PASS' and proof['commit']=='7b32298119df13a83240e082c275c34d184f7ccc' and proof['drafting_release_verified']
 assert not any(Path('/work/application-test-drafts-20260909/ultra-handoff-1').iterdir())
 record.update(status='PASS',reference_files=sorted(set(checked)),preserved_release_files=len(set(preserved)),drafts_started=False)
except BaseException as error:
 record.update(status='FAIL',error=str(error));raise
finally:
 (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 (out/'helper.py').write_bytes(Path(__file__).read_bytes())
 print(record['status'],out)
