"""Tuple-bound entry for the retained metadata engine; no root/workload effects.
Derive the packet namespace and validate the whole current boundary before any
write. The unchanged engine body is reused with that validated namespace.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,stat,sys
SOURCE=Path(__file__).resolve().parent
CONFIG={'path':'/home/holden/mckernel-work/host-preparation/phase5-m03-protection-grace-runtime-binding-20261020-1/positive-s5-runtime-successor-1/tuple-bound-materializer-correction-1/INPUTS.json','sha256':'f392ff8e947a49c1fcc52dcecf7428bd4fa92b4b0aa7bf74dd989164131a2ee0','size':3869,'mode':33152}
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def typed(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=p.lstat().st_mode)
def three(row):return dict(path=row['path'],sha256=row['sha256'],bytes=row['size'])
def exact(row):
 assert type(row) is dict and set(row)=={'path','sha256','size','mode'}
 p=Path(row['path']);assert p.is_absolute() and p.resolve()==p
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode'] and a.st_size==row['size'] and a.st_size<=4<<20
  raw=f.read((4<<20)+1);b=os.fstat(f.fileno());c=p.lstat();assert all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in STABLE)
 assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'];return raw

def inputs():
 cfg=json.loads(exact(CONFIG))
 return dict(cfg=cfg,proposal=json.loads(exact(cfg['base_proposal'])),static=json.loads(exact(cfg['static_inputs'])),seven=json.loads(exact(cfg['seven'])),child=json.loads(exact(cfg['child'])),acceptance=json.loads(exact(cfg['actual_normalization'])))

def select(i):
 cfg=i['cfg'];p=i['proposal'];c=i['static'];x=i['seven'];child=i['child'];a=i['acceptance']
 assert p['static_inputs_template']==cfg['static_inputs'] and p['seven_template']==cfg['seven'] and p['child_command_template']==cfg['child']
 packet=Path(p['static_inputs_template']['path']).parent
 base=Path(cfg['base_proposal']['path']).parent
 assert packet.is_absolute() and packet.resolve()==packet and packet.parent==base==SOURCE.parent
 assert Path(p['seven_template']['path']).parent==packet and Path(p['child_command_template']['path']).parent==SOURCE
 assert c['actual_preparation_acceptance']==cfg['actual_normalization']==p['actual_normalization_acceptance']
 assert c['actual_stage_acceptance']==a['actual_stage_acceptance']==p['actual_stage_acceptance']
 assert c['physical_consumer_actual_acceptance']['path']==cfg['actual_positive_consumer']['path'] and c['physical_consumer_actual_acceptance']['sha256']==cfg['actual_positive_consumer']['sha256']
 assert c['latest_physical']['path']==cfg['actual_positive_physical']['path'] and c['latest_physical']['sha256']==cfg['actual_positive_physical']['sha256']
 pre=json.loads(exact(a['actual_full_preflight']));binding=json.loads(exact(a['actual_binding_result']))
 assert c['binding']==binding==pre['binding']==a['binding']
 assert c['parent_nine_field_identity']==pre['parent_nine_field_identity']==a['facts']['parent_nine_field_identity']
 parent=Path(binding['attempt_parent']);s=parent.lstat();assert not list(parent.iterdir()) and all(getattr(s,k)==v for k,v in pre['parent_nine_field_identity'].items())
 assert x['nonce']==p['nonce']==binding['nonce'] and len(binding['nonce'])==32 and all(v in '0123456789abcdef' for v in binding['nonce'])
 assert x['prospective_attempt_parent']==binding['attempt_parent'] and x['prospective_manifest_path']==binding['manifest']['path']
 assert pre['paths']['qmp_socket_bytes']<=107 and not os.path.lexists(pre['paths']['attempt'])
 assert child['argv']==['/home/holden/anaconda3/bin/python3.9','-I','-B',str(SOURCE/'bind_m03_handshake_native_packet.py'),cfg['actual_normalization']['path'],cfg['actual_normalization']['sha256'],cfg['actual_positive_physical']['path'],cfg['actual_positive_physical']['sha256'],None,None]
 outputs=p['final19_outputs'];captures=x['fresh_capture_and_actual_command_paths']
 source_paths=set(p['source_input_paths'])|{CONFIG['path'],str(Path(__file__).resolve()),cfg['base_proposal']['path'],cfg['frozen_engine']['path'],cfg['static_inputs']['path'],cfg['seven']['path'],cfg['child']['path'],cfg['actual_normalization']['path'],cfg['actual_positive_physical']['path'],cfg['actual_positive_consumer']['path']}
 prior=set(p['prior_output_paths'])
 assert len(outputs)==len(set(outputs))==p['expected_output_count'] and len(captures)==len(set(captures))==p['capture_paths']
 assert set(outputs+captures).isdisjoint(source_paths|prior)
 for path in outputs+captures:
  candidate=Path(path);assert packet in candidate.parents and not os.path.lexists(candidate)
 assert all(Path(r['template']['path']).parent==SOURCE/'capture-template-source' for r in x['steps'])
 assert str(SOURCE/'root_manual_snapshot_m03.py') in x['steps'][0]['argv_template']
 assert x['steps'][3]['argv_template']==c['root_owner_argv']
 generated=[packet/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.json',SOURCE/'FINAL19-CHILD-COMMAND.REVIEW-PENDING.json',base/'S6-Q6-FINAL19-MATERIALIZED-PROPOSAL.json']
 assert len(set(generated))==len(generated) and set(map(str,generated)).isdisjoint(source_paths|prior|set(outputs+captures))
 for path in generated:assert not os.path.lexists(path)
 return dict(packet=packet,generated=generated,source_paths=source_paths)

def real_write(path,value):
 with Path(path).open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
 return three(typed(path))

def generate(i,proof,writer):
 # This function performs the real helper selection/generation. A local test
 # supplies a capture-only writer; production main supplies only real_write.
 selected=select(i);cfg=i['cfg'];exact(cfg['frozen_engine'])
 assert proof['path'] not in set(map(str,selected['generated']))|set(i['proposal']['final19_outputs'])|set(i['seven']['fresh_capture_and_actual_command_paths'])
 selected['source_paths'].add(proof['path'])
 spec=importlib.util.spec_from_file_location('retained_exact_S6_metadata_engine',cfg['frozen_engine']['path'])
 engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
 engine.Q=selected['packet']
 allowed=set(selected['generated']);written=[]
 def checked_write(path,value):
  path=Path(path);assert path in allowed and path not in written
  value=copy.deepcopy(value)
  if path==selected['generated'][0]:
   additions=[three(typed(Path(__file__).resolve())),three(CONFIG)]
   for row in additions:
    if row not in value['runtime_source_refs']:value['runtime_source_refs'].append(row)
   if str(Path(CONFIG['path']).parent) not in value['host_control_source_readonly_roots']:value['host_control_source_readonly_roots'].append(str(Path(CONFIG['path']).parent))
  if path==selected['generated'][2]:
   value['materializer_source']=typed(Path(__file__).resolve())
   value['materializer_argv_template']=['/home/holden/anaconda3/bin/python3.9','-I','-B',str(Path(__file__).resolve()),cfg['actual_normalization']['path'],cfg['actual_normalization']['sha256'],proof['path'],proof['sha256']]
   value['source_input_paths']=sorted(set(value['source_input_paths'])|selected['source_paths'])
  result=writer(path,value);written.append(path);return result
 engine.write=checked_write
 previous=sys.argv
 try:
  sys.argv=[str(Path(__file__).resolve()),cfg['actual_normalization']['path'],cfg['actual_normalization']['sha256'],proof['path'],proof['sha256']]
  engine.main()
 finally:sys.argv=previous
 assert written==selected['generated']
 return selected

def main():
 assert len(sys.argv)==5
 i=inputs();assert sys.argv[1:3]==[i['cfg']['actual_normalization']['path'],i['cfg']['actual_normalization']['sha256']]
 proof=typed(Path(sys.argv[3]));assert proof['sha256']==sys.argv[4]
 p=json.loads(exact(proof));me=typed(Path(__file__).resolve())
 assert p['schema']=='mckernel.root.exact-fetched-source-publication.v1' and p['verified'] is True and p['commit']==p['fetched_commit']
 assert any(r['sha256']==me['sha256'] and r['bytes']==me['size'] and r['mode']==me['mode'] for r in p['rows']),'NEW corrected-source fetched proof is required; old withdrawn proof is not authority'
 generate(i,proof,real_write)
if __name__=='__main__':main()
