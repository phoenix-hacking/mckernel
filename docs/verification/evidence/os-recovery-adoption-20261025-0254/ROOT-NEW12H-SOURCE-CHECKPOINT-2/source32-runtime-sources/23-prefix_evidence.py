"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only reconstruction of actual passed0–7 prefix; never executes old binaries.
"""
from pathlib import Path
import hashlib,json,stat

def need(ok,message):
 if not ok:raise ValueError(message)
def closed(m,leases=0):
 return m['open_fds']==0 and m['duplicate_close']==0 and m['leases']==leases and m['udev_ctx']==0 and m['udev_mon']==0 and m['udev_devices']==0 and m['threads']==1
def capture_ok(c,rc):
 return c.get('returncode')==rc and c.get('direct_child_joined') is True and c.get('group_absent') is True and c.get('closed_streams') is True and c.get('error') is None and c.get('retirement_error') is None and c.get('timed_out') is False and not c.get('unexpected_group_members')
def join(root,label,rc):
 directory=Path(root)/label;c=json.loads((directory/'whole-join.json').read_bytes());need(capture_ok(c,rc),'retained positive child join/status missing: '+label)
 for stream in ['stdout','stderr']:
  raw=(directory/stream).read_bytes();need(len(raw)==c['captures'][stream]['size'] and hashlib.sha256(raw).hexdigest()==c['captures'][stream]['sha256'],'retained captured bytes differ')
 return c
def verify_files(root,rows):
 root=Path(root)
 for row in rows:
  relative=Path(row['relative']);need(not relative.is_absolute() and '..' not in relative.parts,'closed retained path')
  path=root/relative;s=path.lstat();need(stat.S_ISREG(s.st_mode) and not path.is_symlink() and s.st_nlink==1,'retained regular file required')
  raw=path.read_bytes();need(len(raw)==row['source']['bytes'] and hashlib.sha256(raw).hexdigest()==row['source']['sha256'],'retained prefix bytes differ: '+str(relative))
 return len(rows)
def load(root,cases):
 root=Path(root);need(len(cases)==26 and all(case['reference_defined_compare'] for case in cases[:8]) and all(not case['reference_defined_compare'] for case in cases[8:]),'exact historical8/current18 partition')
 for label in ['mock-build','C-reference-build','C-helper-build','Rust-daemon-build']:join(root,label,0)
 failure=json.loads((root/'first-failure.json').read_bytes());need(failure['name']=='full-lifecycle' and failure['passed_contract'] is False and failure['Rust_resources']['threads']==2,'actual old failure must remain failed')
 results=[]
 for i,case in enumerate(cases[:8]):
  r='%02d-Rust'%i;c='%02d-C'%i;p=join(root,r,case['status']);q=join(root,c,case['status'])
  resources=json.loads((root/(r+'.resources.json')).read_bytes());reference=json.loads((root/(c+'.resources.json')).read_bytes())
  trace=(root/(r+'.trace')).read_text().splitlines();ct=(root/(c+'.trace')).read_text().splitlines()
  same=all((root/r/stream).read_bytes()==(root/c/stream).read_bytes() for stream in ['stdout','stderr']) and [line for line in trace if line.startswith('kprint ')]==[line for line in ct if line.startswith('kprint ')]
  ok=p['returncode']==case['status'] and q['returncode']==case['status'] and closed(resources,case['expected_unreleased_leases']) and same
  for field,key in [('expected_gets','get'),('expected_syslog_messages','syslog_messages')]:
   if field in case:ok=ok and resources[key]==case[field]
  need(ok,'actual retained prefix oracle differs: '+case['name'])
  results.append(dict(name=case['name'],passed_contract=True,Rust_status=p['returncode'],Rust_resources=resources,reference=dict(defined_output_status_diagnostic_equal=True,observed_resources=reference,resource_defects_are_not_an_oracle=True),restoration_claim='host mock only, no native credit',evidence_origin='RETAINED_ACTUAL_1fff_PREFIX_0_7'))
 return results
