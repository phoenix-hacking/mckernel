"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One known immutable CID inspect comparison: only full Mounts record order may differ.
All other CLI responses remain byte-exact. Pure comparison; no process/guard/query calls.
"""
import collections,json
CID='52ae1a85fda1adfaa0a0a3c72306a60a6df0144359f0cd6b9ed1d83c2fc2385c'
ARGV=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect',CID]
def pairs(rows):
 out={}
 for key,value in rows:
  if key in out:raise ValueError('duplicate JSON object key')
  out[key]=value
 return out
def nonfinite(value):raise ValueError('nonfinite JSON scalar')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def parsed(raw):
 rows=json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
 assert type(rows) is list and len(rows)==1 and type(rows[0]) is dict and rows[0].get('Id')==CID
 return rows[0]
def mounts(records):
 assert type(records) is list and len(records)==53 and all(type(r) is dict for r in records)
 destinations=[r['Destination'] for r in records]
 assert all(type(d) is str and d.startswith('/') for d in destinations) and len(set(destinations))==len(destinations)
 return collections.Counter(canonical(record) for record in records)
def compare(expected,returncode,stdout,stderr):
 if expected['argv']!=ARGV:
  assert (returncode,stdout,stderr)==(expected['returncode'],expected['stdout'],expected['stderr'])
  return 'PASS_RAW_EXACT_UNCHANGED_CLI'
 assert returncode==expected['returncode']==0 and stderr==expected['stderr']==''
 actual=parsed(stdout);retained=parsed(expected['stdout'])
 actual_mounts=actual.pop('Mounts');retained_mounts=retained.pop('Mounts')
 assert canonical(actual)==canonical(retained),'all non-Mounts keys/values/types/list-order must remain exact'
 assert mounts(actual_mounts)==mounts(retained_mounts),'full mount records must match as multiset with unique Destination'
 return 'PASS_KNOWN_EXACT_CID_FULL_INSPECT_ONLY_MOUNTS_ORDER'
