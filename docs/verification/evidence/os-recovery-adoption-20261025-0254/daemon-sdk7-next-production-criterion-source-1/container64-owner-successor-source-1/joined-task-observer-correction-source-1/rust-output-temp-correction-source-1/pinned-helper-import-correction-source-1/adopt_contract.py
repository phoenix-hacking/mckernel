"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed data/receipt contract for one existing daemon mock batch. No operations on import.
"""
from pathlib import Path
import hashlib,json,os,re,stat
from pinned_helpers import helper
HERE=Path(__file__).resolve().parent
PREPARATION=HERE/'PREPARATION.SOURCE-ONLY.json'
PREPARATION_SHA='dd7e8bfe430c812fd4e10c2085d02b5a43515b889150088aa9a8f9a46617f081'
OUTPUT_PARENT=HERE/'workspace';MIRROR=HERE/'input-mirror';DRIVER=HERE/'adopt_driver.py'
OWNER=HERE/'adopt_owner.py';CUTOFFS=[1793100290.0,882395.5689528405,897734.6960034363]
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'

def need(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def pairs(rows):
 d={}
 for k,v in rows:
  need(k not in d,'duplicate JSON key');d[k]=v
 return d

def json_bytes(raw):return json.loads(raw,object_pairs_hook=pairs)
need(sha(PREPARATION.read_bytes())==PREPARATION_SHA,'frozen mock preparation differs')
PREP=json_bytes(PREPARATION.read_bytes());CANDIDATE=sha(canonical(PREP['source_files']))

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def node(path):
 p=Path(path);s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def regular(path):
 p=Path(path);s=p.lstat();need(not p.is_symlink() and stat.S_ISREG(s.st_mode) and s.st_nlink==1,'regular single-link input required: '+str(p));return s

def source_at(root,row):
 path=Path(root)/row['relative'];s=regular(path);raw=path.read_bytes()
 need(len(raw)==row['source']['bytes'] and sha(raw)==row['source']['sha256'] and stat.S_IMODE(s.st_mode)==row['mode'],'source bytes/mode differ: '+row['relative'])
 need(s.st_uid==s.st_gid==1000,'source UID/GID differs');return path

def verify_mirror(root):
 root=Path(root);need(root.is_absolute() and root.resolve(strict=True)==root and not root.is_symlink(),'canonical mirror root')
 identity=node(root);need(root.is_dir() and identity['uid']==identity['gid']==1000 and identity['mode']==0o700,'private source mirror root')
 expected={row['relative'] for row in PREP['source_files']};files=set()
 output=root/PREP['fixture_output_relative'];need(output.is_dir() and not output.is_symlink() and not list(output.iterdir()),'precreated empty source-side output target')
 for path in root.rglob('*'):
  need(not path.is_symlink(),'source mirror symlink')
  if path.is_file():files.add(str(path.relative_to(root)))
  else:
   s=path.lstat();need(path.is_dir() and s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700,'private mirror directory')
 need(files==expected,'exact source mirror inventory')
 for row in PREP['source_files']:source_at(root,row)
 return sorted(files)

def output_binding(request):
 identity=request['fixture_output_identity'];root=Path(request['candidate_root']);path=root/'fixture-output'
 actual=node(path);need(actual==identity and actual['uid']==actual['gid']==1000 and actual['mode']==0o700 and path.is_dir() and not path.is_symlink(),'fresh output identity differs')
 return dict(schema='mckernel.daemon-mock.precreated-output.v1',path=PREP['container_output'],nonce=request['nonce'],device=actual['device'],inode=actual['inode'],uid=1000,gid=1000,mode=0o700)

def verify_request_inputs(request):
 need(Path(request['input_root'])==MIRROR and node(MIRROR)==request['input_identity'],'exact mirror identity')
 verify_mirror(MIRROR)
 root=Path(request['candidate_root']);need({p.name for p in root.iterdir()}=={'fixture-output'} and not list((root/'fixture-output').iterdir()),'fresh work contains only empty fixture output')
 binding=output_binding(request);reference=request['output_binding'];need(set(reference)=={'path','sha256'},'exact two-key output reference')
 raw=Path(reference['path']).read_bytes();need(sha(raw)==reference['sha256'] and json_bytes(raw)==binding,'actual output binding differs')
 prepdir=Path(request['runtime_preparation_identity']['path']);need(prepdir==OUTPUT_PARENT/('preparation-'+request['nonce']) and node(prepdir)==request['runtime_preparation_identity'],'runtime preparation identity')
 identity=node(prepdir);need(prepdir.is_dir() and not prepdir.is_symlink() and identity['uid']==identity['gid']==1000 and identity['mode']==0o700,'private runtime preparation directory')
 need({p.name for p in prepdir.iterdir()}=={'PREPARATION.SOURCE-ONLY.json','OUTPUT-BINDING.ACTUAL.json'},'runtime preparation inventory')
 need(Path(reference['path'])==prepdir/'OUTPUT-BINDING.ACTUAL.json' and (prepdir/'PREPARATION.SOURCE-ONLY.json').read_bytes()==PREPARATION.read_bytes(),'runtime preparation bytes')
 regular(prepdir/'PREPARATION.SOURCE-ONLY.json');regular(prepdir/'OUTPUT-BINDING.ACTUAL.json')
 verify_retained_prefix(PREP['retained_prefix_host'])
 verify_retained_mock(PREP['retained_mock_host'])
 return binding

def fixture_command(nonce):
 need(re.fullmatch('[0-9a-f]{32}',str(nonce)) is not None,'exact mock nonce')
 return [x.replace('ACTUAL_REQUEST_NONCE',nonce) for x in PREP['command_template']]

def output_tree_bytes(root,maximum):
 root=Path(root);total=count=0
 if not root.exists():return 0
 for path in root.rglob('*'):
  count+=1;need(count<=4096,'bounded output inventory exceeded')
  s=path.lstat()
  if stat.S_ISLNK(s.st_mode):
   need(path==root/'fixture-output/ihkmond','only exact fixture invocation symlink allowed')
   target=os.readlink(path);allowed={str(Path(PREP['container_output'])/name) for name in ['ihkmond-C','ihkmond-Rust','ring-C']}
   need(target in allowed,'fixture symlink target differs');actual=root/'fixture-output'/Path(target).name;regular(actual)
   total+=s.st_size
  elif stat.S_ISREG(s.st_mode):total+=s.st_size
  else:need(stat.S_ISDIR(s.st_mode),'output type differs')
  need(total<=maximum,'bounded output bytes exceeded')
 return total

def capture_ok(c, expected_returncode=0):
 return c.get('returncode')==expected_returncode and c.get('direct_child_joined') is True and c.get('group_absent') is True and c.get('closed_streams') is True and c.get('error') is None and c.get('retirement_error') is None and c.get('timed_out') is False and not c.get('unexpected_group_members')

def cases():
 row=next(x for x in PREP['source_files'] if x['relative'].endswith('/fixture/cases.json'));raw=Path(row['source']['path']).read_bytes();need(sha(raw)==row['source']['sha256'],'cases source differs');return json_bytes(raw)

def closed(resources,leases=0):
 return resources.get('open_fds')==0 and resources.get('duplicate_close')==0 and resources.get('leases')==leases and resources.get('udev_ctx')==0 and resources.get('udev_mon')==0 and resources.get('udev_devices')==0 and resources.get('threads')==1

def validate_summary(summary):
 need(summary.get('status')=='PASS_RETAINED_PREFIX8_AND_CORRECTED_SUFFIX18_MOCK_ONLY' and summary.get('daemon_cases')==26 and summary.get('failed')==[],'exact mock summary')
 need(summary.get('normal_C_ring_parity') is True and summary.get('Rust_oversized_read_proposal') is True,'ring/oversize checks missing')
 need(all(summary.get(k) is False for k in ['production_daemon_fork_executed','real_udev_or_devices_executed','native_acceptance','provider_Rust_link_closure']),'mock scope inflated')
 need(summary.get('retained_prefix_cases')==8 and summary.get('new_corrected_daemon_cases')==18 and summary.get('prefix_reexecuted') is False and summary.get('historical_1fff_failure_remains_failed') is True,'exact mixed8+18 continuation scope required')
 expected=cases();rows=summary.get('results');need(isinstance(rows,list) and len(rows)==26 and [r.get('name') for r in rows]==[r['name'] for r in expected] and all(r.get('passed_contract') is True for r in rows),'all exact26 mock cases required')
 for row,case in zip(rows,expected):
  need(row.get('Rust_status')==case['status'] and closed(row.get('Rust_resources',{}),case['expected_unreleased_leases']),'case status/resources differ')
  resources=row['Rust_resources']
  for field,key in [('expected_gets','get'),('expected_syslog_messages','syslog_messages')]:
   if field in case:need(resources.get(key)==case[field],'exact case counter differs')
  if case['status']==0 and case['expect_mon']:need(resources.get('detect',0)>=1,'monitor detection missing')
  if case['name']=='release-failure-not-claimed-restored':need(resources.get('release_attempts')==1 and resources.get('released')==0,'failed release falsely restored')
  reference=row.get('reference')
  need((reference is None and not case['reference_defined_compare']) or (case['reference_defined_compare'] and isinstance(reference,dict) and reference.get('defined_output_status_diagnostic_equal') is True),'defined C reference parity missing')
 return summary

def verify_retained_prefix(root):
 prefix=helper('prefix');verify_files=prefix.verify_files;load=prefix.load
 count=verify_files(root,PREP['retained_prefix_files']);load(root,cases());return count

def validate_fixture_tree(root,prefix=None,mock_prefix=None,fixture_pid=None):
 validate_audit=helper('audit').validate
 load=helper('prefix').load
 root=Path(root);prefix=Path(PREP['retained_prefix_host']) if prefix is None else Path(prefix)
 mock_prefix=Path(PREP['retained_mock_host']) if mock_prefix is None else Path(mock_prefix)
 verify_retained_mock(mock_prefix)
 regular(root/'mock.o');need((root/'mock.o').read_bytes()==(mock_prefix/'mock.o').read_bytes(),'exact passed d413 mock object required')
 verify_retained_prefix(prefix)
 validate_receipt=helper('rustio').validate_receipt
 command=json_bytes((root/'Rust-daemon-build.command.json').read_bytes())
 recorded_command=json_bytes((root/'Rust-daemon-build/command.json').read_bytes())
 need(recorded_command['argv']==command['argv'] and recorded_command['cwd']==command['cwd'],'actual child compiler argv/cwd differs')
 baseline=json_bytes((mock_prefix/'Rust-daemon-build.command.json').read_bytes())['argv']
 validate_receipt(json_bytes((root/'Rust-output-preflight.ACTUAL.json').read_bytes()),PREP['container_output'],root,command,fixture_pid,baseline)
 summary=json_bytes((root/'summary.json').read_bytes());validate_summary(summary)
 need(summary['results'][:8]==load(prefix,cases()),'retained actual prefix must not be relabeled')
 need(not (root/'first-failure.json').exists(),'current first failure retained')
 expected={label:0 for label in ['Rust-daemon-build','ring-C','ring-Rust','oversize-Rust']}
 for i,case in enumerate(cases()[8:],8):expected['%02d-Rust'%i]=case['status']
 actual={p.parent.name for p in root.glob('*/whole-join.json')};need(actual==set(expected),'exact one Rust compiler +18 suffix +ring/oversize joins only; no mock/prefix replay')
 for label in sorted(expected):
  capture=json_bytes((root/label/'whole-join.json').read_bytes());need(capture_ok(capture,expected[label]),'new suffix child join failed: '+label)
  for stream in ['stdout','stderr']:
   raw=(root/label/stream).read_bytes();need(len(raw)==capture['captures'][stream]['size'] and sha(raw)==capture['captures'][stream]['sha256'],'new suffix stream differs')
  if label.endswith('Rust') or label=='oversize-Rust':
   audit=(root/(label+'.joined-tasks.ndjson')).read_bytes();proof=validate_audit(audit,capture['pid'],capture['start']);need(json_bytes((root/(label+'.joined-tasks.proof.json')).read_bytes())==proof,'durable real join audit differs')
 for i,(case,row) in enumerate(zip(cases()[8:],summary['results'][8:]),8):
  label='%02d-Rust'%i;resources=json_bytes((root/(label+'.resources.json')).read_bytes());need(resources==row['Rust_resources'],'durable suffix resources differ')
  trace=(root/(label+'.trace')).read_text().splitlines()
  if case['name']=='configured-facility':need(any('facility=144' in line for line in trace),'configured facility trace missing')
  if 'expected_event_read_fault' in case:need(any(('injected '+case['expected_event_read_fault']) in line for line in trace),'expected read fault trace missing')
 rings=[]
 for label in ['ring-C','ring-Rust']:
  resources=json_bytes((root/(label+'.resources.json')).read_bytes());need(closed(resources),'ring resource closure differs')
  trace=(root/(label+'.trace')).read_text().splitlines();files=json_bytes((root/(label+'.files.json')).read_bytes());rings.append(([line for line in trace if line.startswith('syslog ')],files.get('kmsg0')))
 need(rings[0]==rings[1],'actual C/Rust ring bytes differ')
 oversized=json_bytes((root/'oversize-Rust.resources.json').read_bytes());need(closed(oversized) and oversized.get('syslog_bytes')==(1<<20)+16,'oversize bytes or closure differ')
 for name in ['ihkmond-C','ring-C']:
  retained=prefix/name;actual=root/name;regular(actual);need(actual.read_bytes()==retained.read_bytes(),'reused C executable differs')
 regular(root/'ihkmond-Rust.o');need((root/'ihkmond-Rust.o').stat().st_size>0,'retain new Rust relocatable; no old Rust object existed')
 return summary


def verify_retained_mock(root):
 prefix=helper('prefix');verify_files=prefix.verify_files;join=prefix.join
 count=verify_files(root,PREP['retained_mock_files']);join(root,'mock-build',0);join(root,'Rust-daemon-build',1)
 raw=(Path(root)/'Rust-daemon-build/stderr').read_text()
 need("couldn't create a temp dir" in raw and 'Read-only file system' in raw and '/rmeta' in raw,'exact retained output-directory failure required')
 need(not any(Path(root).glob('[0-9][0-9]-Rust')),'old d413 suffix did not execute')
 return count
