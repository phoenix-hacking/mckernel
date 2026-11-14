"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed data/receipt contract for one existing daemon mock batch. No operations on import.
"""
from pathlib import Path
import hashlib,json,os,re,stat
from pinned_helpers import helper
HERE=Path(__file__).resolve().parent
PREPARATION=HERE/'PREPARATION.SOURCE-ONLY.json'
PREPARATION_SHA='c87b68e86748f43e9e26a0c322e05d8f0de154c9c5f6072ed9721eaadab5ebf4'
OUTPUT_PARENT=HERE/'workspace';MIRROR=HERE/'input-mirror';DRIVER=HERE/'final_driver.py'
OWNER=HERE/'final_owner.py';CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]
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
 need({p.name for p in prepdir.iterdir()}=={'PREPARATION.SOURCE-ONLY.json','OUTPUT-BINDING.ACTUAL.json','RETAINED-INPUTS.SOURCE-ONLY.json'},'runtime preparation inventory')
 need(Path(reference['path'])==prepdir/'OUTPUT-BINDING.ACTUAL.json' and (prepdir/'PREPARATION.SOURCE-ONLY.json').read_bytes()==PREPARATION.read_bytes(),'runtime preparation bytes')
 regular(prepdir/'PREPARATION.SOURCE-ONLY.json');regular(prepdir/'OUTPUT-BINDING.ACTUAL.json');regular(prepdir/'RETAINED-INPUTS.SOURCE-ONLY.json')
 need((prepdir/'RETAINED-INPUTS.SOURCE-ONLY.json').read_bytes()==(HERE/'RETAINED-INPUTS.SOURCE-ONLY.json').read_bytes(),'exact retained current manifest export')
 validate_retained_current()
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
   target=os.readlink(path);allowed={str(Path(PREP['container_output'])/name) for name in ['ihkmond-Rust','ring-C-helper']}
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
 need(summary.get('status')=='PASS_RETAINED26_AND_FINAL_THREE_MOCK_ONLY','exact three-call summary')
 need(summary.get('retained_daemon_cases')==26 and summary.get('new_daemon_cases')==0 and summary.get('compilers_executed')==0 and summary.get('remaining_invocations_executed')==3,'exact retained/current counts')
 need(summary.get('normal_C_ring_parity') is True and summary.get('Rust_oversized_read_proposal') is True,'ring/oversize checks required')
 need(all(summary.get(k) is False for k in ['native_acceptance','provider_Rust_link_closure','M15_file_closure']),'mock scope inflated')
 return summary

def validate_retained_current(root=None,prefix=None,mock_prefix=None):
 from retained_current import validate
 return validate(Path(PREP['retained_current_host']) if root is None else Path(root),next(r['source']['path'] for r in PREP['source_files'] if r['relative'].endswith('/fixture/cases.json')),HERE/'RETAINED-INPUTS.SOURCE-ONLY.json',Path(PREP['retained_prefix_host']) if prefix is None else Path(prefix),Path(PREP['retained_mock_host']) if mock_prefix is None else Path(mock_prefix))

def verify_retained_prefix(root):
 prefix=helper('prefix');verify_files=prefix.verify_files;load=prefix.load
 count=verify_files(root,PREP['retained_prefix_files']);load(root,cases());return count

def validate_fixture_tree(root,prefix=None,mock_prefix=None,fixture_pid=None,retained=None):
 root=Path(root);retained=Path(PREP['retained_current_host']) if retained is None else Path(retained)
 summary=validate_summary(json_bytes((root/'summary.json').read_bytes()))
 need(summary['results']==validate_retained_current(retained,prefix,mock_prefix),'retained26 evidence must not be relabeled')
 need(not (root/'first-failure.json').exists(),'current failure receipt exists')
 expected={'ring-C','ring-Rust','oversize-Rust'}
 need({p.parent.name for p in root.glob('*/whole-join.json')}==expected,'exact final three joins; no compiler or completed case replay')
 for label in sorted(expected):
  capture=helper('prefix').join(root,label,0)
  command=json_bytes((root/label/'command.json').read_bytes())
  need(command==dict(argv=[str(Path(PREP['container_output'])/'ihkmond')],cwd=PREP['fixture_base'],label=label),'exact suffix invocation argv/cwd/label')
  if label!='ring-C':
   proof=helper('audit').validate((root/(label+'.joined-tasks.ndjson')).read_bytes(),capture['pid'],capture['start'])
   need(proof==json_bytes((root/(label+'.joined-tasks.proof.json')).read_bytes()),'durable Rust helper join audit differs')
  need(closed(json_bytes((root/(label+'.resources.json')).read_bytes())),'helper resource closure differs')
 rings=[]
 for label in ['ring-C','ring-Rust']:
  lines=(root/(label+'.trace')).read_text().splitlines();files=json_bytes((root/(label+'.files.json')).read_bytes())
  need(isinstance(files.get('kmsg0'),str),'written kmsg0 receipt required')
  rings.append(([line for line in lines if line.startswith('syslog ')],files['kmsg0']))
 need(rings[0]==rings[1],'actual C/Rust ring bytes/logs differ')
 need(json_bytes((root/'oversize-Rust.resources.json').read_bytes())['syslog_bytes']==(1<<20)+16,'exact oversized read bytes')
 for source,target in [('ring-C','ring-C-helper'),('ihkmond-Rust','ihkmond-Rust')]:
  regular(root/target);need((root/target).read_bytes()==(retained/source).read_bytes(),'reused executable differs')
 return summary


def verify_retained_mock(root):
 prefix=helper('prefix');verify_files=prefix.verify_files;join=prefix.join
 count=verify_files(root,PREP['retained_mock_files']);join(root,'mock-build',0);join(root,'Rust-daemon-build',1)
 raw=(Path(root)/'Rust-daemon-build/stderr').read_text()
 need("couldn't create a temp dir" in raw and 'Read-only file system' in raw and '/rmeta' in raw,'exact retained output-directory failure required')
 need(not any(Path(root).glob('[0-9][0-9]-Rust')),'old d413 suffix did not execute')
 return count
