import json,hashlib,os,stat
from pathlib import Path
H=Path('/home/holden/mckernel-work/host-preparation')
D2=H/'current-host-pair-205-two-rounds-20261019-1/stage-preparation-1'; Q2=D2/'native-packet-1'
D=H/'current-host-pair-205-three-rounds-20261020-1/stage-preparation-1'; Q=D/'native-packet-1'
R2=H/'current-host-pair-205-two-rounds-independent-review-20261019-1'; R=H/'current-host-pair-205-three-rounds-independent-review-20261020-1'
C2=H/'current-host-rust-pair-native-snapshot-20261019-1/two-round205-case-1'; C=H/'current-host-rust-pair-native-snapshot-20261019-1/three-round205-case-1'
def read(p): return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,x):
 raw=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 with Path(p).open('xb') as f:f.write(raw)
 return ref(p)
old=read(Q2/'FINAL-SEVEN-ROOT-CALL-DATA-v2.json'); ancestry=old['historical_template_ancestry']
repls=[(str(D2),str(D)),(str(R2),str(R)),(str(C2),str(C)),('r2052-261019-1','r2053-261020-1'),('r2052m-261019-1','r2053m-261020-1'),('21b78b668471498fb68fa9cbfd57b2c6','b9d2e9af8064437b9d7f08c66c98ac20'),('eb380f5514ffbb7165e3f83f9aeaa565060df2baf8ba73cae67328ff1e7bc17b',ref(Q/'machine-base.json')['sha256'])]
def transform(x):
 if isinstance(x,str):
  for a,b in repls:x=x.replace(a,b)
  return x
 if isinstance(x,list):return [transform(i) for i in x]
 if isinstance(x,dict):return {k:transform(v) for k,v in x.items()}
 return x
x=transform(old); x['historical_template_ancestry']=ancestry
projpath=C/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json'; proj=read(projpath)
config=ref(R/'FINAL-IHK-LOGGING-CHECK-CONFIG.json'); sourceindex=read(Q/'FINAL-NONTEMPORAL-DATA-INDEX.json'); proposal=read(Q/'proposal.json')
x.update(final_config=config,machine_base=ref(Q/'machine-base.json'),non_temporal_index=ref(Q/'FINAL-NONTEMPORAL-DATA-INDEX.json'),snapshot_projection=ref(projpath),native_allowed_argv=proposal['argv'])
# The actual producer's snapshot command comes from the independent DATA owner's exact argv.
# Explicitly fixed below from exact independent projection shape.
argvkey='root_snapshot_argv'
x['steps'][0]['argv_template']=proj[argvkey]
x['steps'][2]['argv_template'][x['steps'][2]['argv_template'].index('--config-sha256')+1]=config['sha256']
x['steps'][3]['argv_template']=proposal['argv']
# Each new template preserves both operations and accepted f2db profile interface.
(Q/'capture-templates').mkdir(mode=0o700,exist_ok=False)
(Q/'actual-command-data').mkdir(mode=0o700,exist_ok=False)
for row,prior in zip(x['steps'],old['steps']):
 if row['index']>0:Path(row['stdout']).parent.mkdir(mode=0o700,parents=True,exist_ok=False)
 t=transform(read(prior['template']['path']))
 t['release']=sourceindex['static_review'];t['root_installed_release_path']=sourceindex['static_review']['path']
 t['operations'][1]['argv_template']=row['argv_template']
 for k in ('stdout','stderr','status'):t['operations'][1][k+'_path']=row[k]
 row['template']=write(Q/'capture-templates'/Path(prior['template']['path']).name,t)
parents=sorted({str(Q/'actual-command-data')}|{str(Path(r['stdout']).parent) for r in x['steps']})
x['capture_parents']=[]
for p in parents:
 s=Path(p).lstat();assert stat.S_ISDIR(s.st_mode) and s.st_uid==1000 and s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700
 x['capture_parents'].append({'path':p,'identity':{'device':s.st_dev,'inode':s.st_ino,'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode))}})
assert len(parents)==8
fresh=[p for row in x['steps'] for p in row['capture_outputs']+[row['materialized_command_data']]]
assert len(fresh)==49 and len(set(fresh))==49 and all(not Path(p).exists() for p in fresh)
x['fresh_capture_and_actual_command_paths']=fresh
assert x['steps'][1]['argv_template'][-2]==x['machine_base']['sha256']
assert x['steps'][3]['argv_template']==x['native_allowed_argv']
assert '--exclude=./qmp.sock' in x['steps'][6]['argv_template']
assert not Path(x['final_machine_output']).exists() and not Path(x['snapshot_output']).exists()
print(json.dumps(write(Q/'FINAL-SEVEN-ROOT-CALL-DATA.json',x)))
