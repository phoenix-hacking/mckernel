# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import json,copy
from pathlib import Path
j=json.loads(Path('SCRIPTS-OVERLAY.NOT-RELEASED.json').read_text())
keys={'path','type','mode','bytes','sha256','link_target'}
def expected_entries():return [{k:v for k,v in x.items() if k in keys} for x in j['base_members']+j['additions']]
def check(items):
 expected=expected_entries(); e={x['path']:x for x in expected}; a={x['path']:{k:v for k,v in x.items() if k in keys} for x in items}
 return len(e)==len(expected) and len(a)==len(items) and a==e
valid=expected_entries();assert check(valid)
for bad in [valid[:-1],valid+[valid[0]],valid+[{'path':'unexpected','type':'file','mode':'0644','bytes':0,'sha256':'0'*64}]]: assert not check(bad)
for key,value in [('mode','0000'),('sha256','0'*64),('type','symlink')]:
 bad=copy.deepcopy(valid);i=next(i for i,x in enumerate(bad) if x['type']=='file');bad[i][key]=value;assert not check(bad)
print('PASS model rejects missing, duplicate, extra, wrong mode/hash/type; synthetic union only, no materialization')
