"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read postgrowth state only; original ratio-fault and custody remain untouched.
"""
from pathlib import Path
import json, os, time, subprocess, hashlib, importlib.util
E=Path(__file__).resolve().parent.parent
P=Path(__file__).resolve().parent
S=E/'scratch-growth-sdk7-110-to-142g-source-1/grow_scratch.py'
assert hashlib.sha256(S.read_bytes()).hexdigest()=='8229919524d803c3694aea42e85bb43d705228d7f78a8ce768704b613ce7608f'
spec=importlib.util.spec_from_file_location('readonly_helpers',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=json.loads((P/'ROOT-ACTUAL-GROWTH-CONTRACT.json').read_text())
preserved=m.file_manifest(c)
def proc(pid):
 p=Path('/proc')/str(pid);raw=(p/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
 return {'pid':pid,'birth':int(fields[19]),'pgrp':int(fields[2]),'raw_stat':raw,
 'cmdline_hex':(p/'cmdline').read_bytes().hex(),'status':(p/'status').read_text(),
 'children':(p/'task'/str(pid)/'children').read_text()}
owner=proc(1281419);caller=proc(1281416)
assert caller['birth']==85204885 and owner['pgrp']==caller['pgrp'] and not owner['children'].strip()
assert str(S).encode().hex() in owner['cmdline_hex']
fd=Path('/proc/1281419/fd/4');meta=os.stat(fd);assert (meta.st_dev,meta.st_ino)==(27,4)
fdinfo=Path('/proc/1281419/fdinfo/4').read_text();locks=Path('/proc/locks').read_text()
matching=[line for line in locks.splitlines() if '00:1b:4 ' in line]
assert len(matching)==1 and '1281419' in matching[0].split()
events=[json.loads(line) for line in (P/'OUTPUT/journal.jsonl').read_text().splitlines()]
waited=[event for event in events if event['event']=='child_waited']
assert len(waited)==5 and all(event['data']['returncode']==0 for event in waited)
q=events[-1]
assert q['event']=='QUARANTINE' and q['data']['fd']==4
assert q['data']['unjoined_child'] is False and q['data']['spawn_acquisition_pending'] is False
assert all(child['positive_wait'] for child in q['data']['children'])
back=os.lstat(m.BACKING);assert dict(path=m.BACKING,**m.ident(back),uuid=m.UUID)==m.expected(m.NEW)
lp=Path('/sys/block/loop36')
loop={key:(lp/key).read_text().strip() for key in ['size','loop/backing_file','loop/offset','loop/sizelimit','loop/autoclear','ro']}
assert int(loop['size'])*512==m.NEW and loop['loop/backing_file']==m.BACKING
assert loop['loop/offset']==loop['loop/sizelimit']==loop['ro']=='0' and loop['loop/autoclear']=='1'
argv=['/usr/sbin/dumpe2fs','-h','/dev/loop36'];r=subprocess.run(argv,capture_output=True,text=True,timeout=30)
assert r.returncode==0;fs=m.fs_fields(r.stdout)
assert fs=={'uuid':m.UUID,'blocksize':4096,'blocks':37224448,'reserved':288358}
mount=subprocess.run(['/usr/bin/findmnt','-J','-T',m.MOUNT,'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],capture_output=True,text=True,timeout=10)
assert mount.returncode==0
expected=json.loads((E/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json').read_text())['mount']
assert json.loads(mount.stdout)['filesystems']==[expected]
census=[];errors=[];exited=[]
for path in Path('/proc').iterdir():
 if not path.name.isdecimal():continue
 try:
  raw=(path/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
  census.append({'pid':int(path.name),'pgrp':int(fields[2]),'raw_stat':raw})
 except FileNotFoundError as error:
  if path.exists():errors.append({'pid':path.name,'error':repr(error)})
  else:exited.append({'pid':path.name,'directory_confirmed_absent':True})
 except (OSError,ValueError) as error:errors.append({'pid':path.name,'error':repr(error)})
assert not errors
capacity={name:os.statvfs(name).f_bavail*os.statvfs(name).f_frsize for name in ['/home/holden/mckernel',m.MOUNT]}
assert capacity['/home/holden/mckernel']>=16*2**30 and capacity[m.MOUNT]>=14091616256
result={'scope':__doc__.splitlines()[0],'status':'READONLY_POSTGROWTH_OBSERVER_FAULT_QUALIFICATION_PENDING_REVIEW',
'observed_wall':time.time(),'original_postcheck_fault_preserved':q,'actual_5_commands_all_waited':waited,
'owner':owner,'caller':caller,'root_mutex_fd':{'fd':4,'identity':m.ident(meta),'fdinfo':fdinfo,'global_row':matching},
'backing':dict(path=m.BACKING,**m.ident(back),allocated_bytes=back.st_blocks*512),'loop':loop,'fresh_geometry':fs,
'fresh_dumpe2fs':{'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},'mount':json.loads(mount.stdout),
'current_preservation_comparisons':preserved,'reserve_before':288358,'reserve_after':fs['reserved'],
'no_separate_reserve_mutation':True,'all_process_rows':census,'census_errors':errors,'census_confirmed_exits':exited,
'target_group_members':[row for row in census if row['pgrp']==owner['pgrp']],'capacity':capacity,'no_new_growth_or_release':True}
print(json.dumps(result,indent=2))
