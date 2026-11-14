#!/usr/bin/env python3
"""Unprivileged source/fixture checks; never run the recovery executor."""
import ast
import copy
from decimal import Decimal
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-retirement-postflight-76ae20b5-1.py'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
M=load('postflight_packet',PACKET)
O=load('postflight_test_observer',ROOT/M.OBSERVER_REL)

class PostflightTests(unittest.TestCase):
 def setUp(self):
  # O_NOATIME requires ownership or CAP_FOWNER. Simulate that capability only
  # for read-only ancestor directories; fixture files/root keep real NOATIME.
  original=os.open
  def unprivileged_ancestors(path,flags,*args,**kwargs):
   if flags&os.O_DIRECTORY and flags&os.O_NOATIME:
    info=os.stat(path,dir_fd=kwargs.get('dir_fd'),follow_symlinks=False)
    if info.st_uid!=os.geteuid():flags&=~os.O_NOATIME
   return original(path,flags,*args,**kwargs)
  patch=mock.patch.object(M.os,'open',side_effect=unprivileged_ancestors);patch.start();self.addCleanup(patch.stop)
 def test_unreleased_stops_before_any_privilege_or_file_access(self):
  with mock.patch.object(M.os,'geteuid',side_effect=AssertionError('root queried')),mock.patch.object(M,'PinnedFile',side_effect=AssertionError('file read')):
   with self.assertRaisesRegex(M.Error,'DRAFT_NOT_RELEASED'):M.execute('anything')

 def test_fixed_bindings_preserve_all_five_exclusions_and_failure(self):
  inputs=M.fixed_release_inputs()
  self.assertEqual([x['inode'] for x in inputs['locks']],[31508,31509,31510,31511,31512])
  self.assertEqual(len(inputs['locks']),5)
  self.assertTrue(all(x['immutable'] and x['uid']==x['gid']==0 and x['mode']==0o600 for x in inputs['locks']))
  self.assertEqual(inputs['archive']['size'],10874880)
  self.assertEqual(inputs['source_evidence']['inode'],69508)
  self.assertEqual(inputs['source_evidence']['special']['packet.failure'],M.FAILURE_SHA)
  self.assertEqual(inputs['rounds'],3)
  self.assertFalse(any(inputs[k] for k in ('retirement','deletion','lock_removal')))
  self.assertEqual(inputs['protected']['seal']['inode'],4849667)

 def test_historical_identity_is_preserved_separately_from_live_admission(self):
  evidence=M.fixed_release_inputs()['source_evidence']
  self.assertEqual(evidence['historical_identity_sha256'],'e98cf2d252150c5afba4725995b550cca67352a771f7dda67f5995793e386008')
  self.assertEqual(evidence['admission_identity_sha256'],'f00e5da2d9f426477f29f2102426c7a0346b7cf7e9c4a9593f3743c227cdf9cb')
  self.assertNotEqual(M.IDENTITY_SHA,M.LIVE_IDENTITY_SHA)
  self.assertTrue(evidence['stable_noatime_snapshots'])

 def test_prior_postflight_failure_and_fresh_namespace_are_bound(self):
  prior=M.fixed_release_inputs()['prior_postflight']
  self.assertEqual(prior['source_evidence']['inode'],69537)
  self.assertEqual(prior['source_evidence']['historical_identity_sha256'],prior['source_evidence']['admission_identity_sha256'])
  self.assertEqual(prior['archive']['size'],2375680)
  self.assertEqual(set(prior['source_evidence']['special']),{'packet.failure','post-delete-scan-1.json','post-delete-scan-2.json'})
  self.assertNotEqual(M.OUTPUT,M.PRIOR_DIR)
  self.assertEqual(M.OUTPUT.name,'.mckernel-retirement-postflight-76ae20b5-2')

 def test_no_destructive_retry_docker_sudo_or_source_hash_override(self):
  tree=ast.parse(PACKET.read_text())
  forbidden={'retire','remove_root','unlink','rmdir','rename','rename_noreplace','docker_callback'}
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):self.assertNotIn(node.func.attr,forbidden)
   if isinstance(node,ast.Assign):
    for target in node.targets:
     if isinstance(target,ast.Attribute):self.assertNotIn(target.attr,('source_hash','load_retained_baseline'))
  self.assertNotIn('sudo',str([n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('/usr/bin/')]))

 def test_corrected_and_predecessor_sources_are_separate(self):
  self.assertEqual(M.digest((ROOT/M.OBSERVER_REL).read_bytes()),M.OBSERVER_SHA)
  self.assertEqual(M.digest((ROOT/M.SUPPORT_REL).read_bytes()),M.SUPPORT_SHA)
  self.assertNotEqual(M.OBSERVER_SHA,M.PREDECESSOR_SHA)

 def test_mechanical_finalization_changes_only_unique_sentinel(self):
  raw=PACKET.read_bytes();final=M.final_bytes(raw,'a'*64)
  self.assertEqual(final.replace(b"RELEASE_SHA256='"+b'a'*64+b"'",b"RELEASE_SHA256='RELEASE_HASH_REQUIRED'"),raw)
  for invalid in ('','x'*64,'a'*63):
   with self.assertRaises(M.Error):M.final_bytes(raw,invalid)
  with self.assertRaises(M.Error):M.final_bytes(raw+raw,'a'*64)

 def test_pinned_noatime_file_rejects_replace_symlink_and_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'record';p.write_bytes(b'evidence');os.utime(p,ns=(1000000000,2000000000))
   before=p.stat().st_atime_ns;pin=M.PinnedFile(p,M.digest(b'evidence'))
   try:
    pin.assert_held();self.assertEqual(before,p.stat().st_atime_ns)
    p.rename(Path(directory)/'old');p.write_bytes(b'evidence')
    with self.assertRaisesRegex(M.Error,'identity changed'):pin.assert_held()
   finally:pin.close()
   before_fds=set(os.listdir('/proc/self/fd'))
   with self.assertRaises(M.Error):M.PinnedFile(p,'0'*64)
   self.assertEqual(before_fds,set(os.listdir('/proc/self/fd')))
   p.unlink();p.symlink_to(Path(directory)/'old')
   with self.assertRaises(OSError):M.PinnedFile(p)
   self.assertEqual(before_fds,set(os.listdir('/proc/self/fd')))

 def test_source_execution_uses_sealed_descriptor_bytes(self):
  source=b'import hashlib\ndef source_hash():\n with open(__file__, "rb") as source:\n  return hashlib.sha256(source.read()).hexdigest()\n'
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'source.py';p.write_bytes(source);os.utime(p,ns=(1000000000,2000000000));pin=M.PinnedFile(p,M.digest(source));module=None
   try:
    module=M.module_from(pin,'sealed_fixture')
    self.assertEqual(module.source_hash(),M.digest(source));pin.assert_held()
    flags=fcntl.fcntl(module._postflight_source_fd,fcntl.F_GET_SEALS)
    self.assertTrue(flags&fcntl.F_SEAL_WRITE)
    with self.assertRaises(OSError):os.write(module._postflight_source_fd,b'changed')
   finally:
    if module is not None:os.close(module._postflight_source_fd)
    pin.close()

 def predecessor(self):
  roots=[];released=[]
  for q,original,(dev,ino) in zip(O.QUARANTINE,O.ORIGINAL,O.ROOT_IDS):
   root=(dev,ino,0,0,stat.S_IFDIR,0o700);member=(dev,ino+1,1000,1000,stat.S_IFREG,0o644);members={root,member}
   roots.append({'path':str(q),'device_number':dev,'inode':ino,'device':'0:26','uid':0,'gid':0,'mode':'0700','filesystem_root':'/'+q.name,'tree_root_identity':list(root),'tree_member_identities':[list(x) for x in sorted(members)],'tree_inode_count':2,'tree_membership_sha256':O.membership_digest(members)})
   released.append({'path':str(original),'root':{'device':dev,'inode':ino},'members':[{'device':dev,'inode':ino+1,'uid':1000,'gid':1000,'kind':'file','mode':0o644}]})
  clean={'clean':True,'complete_mount_proofs':True,'closure_nonconvergent':False,'target_references':[],'permission_denials':[],'tree_revalidation_failures':[],'unscanned_final_identities':[],'unresolved_churn':[]}
  mount={'device':'0:26','root':'/','mountpoint':'/dev/shm','filesystem':'tmpfs','mount_id':'24','parent_id':'1','options':'rw','optional_fields':[],'source':'tmpfs','super_options':['rw']}
  baseline={'schema':'mckernel.read-only-live-reference-snapshot.v7','status':'PASS','scan_complete':True,'boot_id':M.BOOT,'observer_sha256':M.PREDECESSOR_SHA,'failure':None,'roots':roots,'canonical_dev_shm':mount,'persistent_tree_revalidation_failures':[],'rounds':[copy.deepcopy(clean),copy.deepcopy(clean)]}
  release={'observer':{'observer_sha256':M.PREDECESSOR_SHA},'boot_id':M.BOOT,'roots':released}
  return baseline,release

 def test_predecessor_validation_explicitly_accepts_only_old_released_members(self):
  baseline,release=self.predecessor();targets,reference,inodes=M.validate_predecessor(baseline,release,O)
  self.assertEqual(len(targets),4);self.assertEqual(len(inodes),4)
  for mutation in ('source','member','count','mount','closure','release'):
   with self.subTest(mutation=mutation):
    b,r=copy.deepcopy((baseline,release))
    if mutation=='source':b['observer_sha256']=M.OBSERVER_SHA
    if mutation=='member':b['roots'][0]['tree_member_identities'][0][1]+=500
    if mutation=='count':b['roots'][0]['tree_inode_count']=1
    if mutation=='mount':b['roots'][0]['filesystem_root']='/wrong'
    if mutation=='closure':b['rounds'][-1]['unresolved_churn']=[{}]
    if mutation=='release':r['observer']['observer_sha256']=M.OBSERVER_SHA
    with self.assertRaises(M.Error):M.validate_predecessor(b,r,O)

 def round(self):
  row={'schema':'mckernel.post-delete-live-reference-round.v1','status':'PASS','round':1,'scan_complete':True,'observer_sha256':M.OBSERVER_SHA,'baseline_sha256':M.BASELINE_SHA,'retained_inode_count':1,'task_churn':False,'closure_nonconvergent':False,'censuses':[[[10,10,'20']],[[10,10,'20']]],'records':[{'identity':[10,10,'20'],'successful':True,'state':'same','references':[],'denials':[],'incomplete':[],'mount_proof':{'complete':True,'identity':[10,10,'20']}}]}
  row.update(closure_passes=1,task_census_changed=False,reconciled_exits=[])
  row.update({k:[] for k in ('path_failures_before','path_failures_after','target_references','permission_denials','incomplete','identity_replacements','entry_churn','unscanned_final_identities')});return row

 def changing_round(self):
  row=self.round();a=[10,10,'20'];b=[11,11,'21'];c=[12,12,'22']
  row['censuses']=[[a,b],[a,c],[a,c]];row['closure_passes']=2;row['task_census_changed']=True
  row['reconciled_exits']=[{'identity':b,'resolution':'exited'}]
  exited={'identity':b,'successful':False,'state':'exited','references':[],'denials':[],'incomplete':[],'mount_proof':None}
  added=copy.deepcopy(row['records'][0]);added['identity']=c;added['mount_proof']['identity']=c
  row['records'].extend([exited,added]);return row

 def test_v2_exact_exit_and_scanned_addition_pass(self):
  row=self.changing_round();M.validate_round(row,1,{(26,2)})
  # A successful complete scan followed by exit is also reconciled.
  row['records'][1].update(successful=True,state='same',mount_proof={'complete':True,'identity':[11,11,'21']})
  M.validate_round(row,1,{(26,2)})

 def test_real_observer_v2_records_accept_in_memory_and_serialized_identities(self):
  a=(10,10,'20');b=(11,11,'21');c=(12,12,'22');snapshots=iter(({a,b},{a,c},{a,c}))
  def scanner(who):
   return {'identity':who,'successful':who!=b,'state':'exited' if who==b else 'same','references':[],'denials':[],'incomplete':[],'expected_absences':[],'mount_proof':None if who==b else {'complete':True,'identity':who}}
  with mock.patch.object(O,'source_hash',return_value=M.OBSERVER_SHA):
   row=O.post_delete_round(1,M.BASELINE_SHA,[],{}, {(26,2)},scanner=scanner,snapshot=lambda:next(snapshots),absence_reader=lambda:[])
  M.validate_round(row,1,{(26,2)})
  M.validate_round(M.decode(M.encoded(row)),1,{(26,2)})

 def test_v2_rejects_unresolved_states_reuse_and_forged_diagnostics(self):
  for case in ('reused','unknown','exit_final','exit_success','exit_reference','exit_denial','exit_incomplete','unscanned_add','replacement','reuse_census','diagnostic','exits_missing','exits_extra','entry_churn','record_entry_churn','nonconvergent','task_churn','missing_final','passes','duplicate','unknown_record'):
   with self.subTest(case=case):
    row=self.changing_round();record=row['records'][1]
    if case in ('reused','unknown'):record['state']=case
    elif case=='exit_final':row['censuses'][-1].append([11,11,'21']);row['reconciled_exits']=[]
    elif case=='exit_success':record['successful']=True
    elif case=='exit_reference':record['references']=[{}]
    elif case=='exit_denial':record['denials']=[{}]
    elif case=='exit_incomplete':record['incomplete']=[{}]
    elif case=='unscanned_add':row['records'].pop()
    elif case=='replacement':row['identity_replacements']=[{}]
    elif case=='reuse_census':row['censuses'][-1][0]=[10,10,'999']
    elif case=='diagnostic':row['task_census_changed']=False
    elif case=='exits_missing':row['reconciled_exits']=[]
    elif case=='exits_extra':row['reconciled_exits'].append({'identity':[99,99,'99'],'resolution':'exited'})
    elif case=='entry_churn':row['entry_churn']=[{}]
    elif case=='record_entry_churn':record['expected_absences']=[{'reason':'per-entry-procfs-absence'}]
    elif case=='nonconvergent':row['closure_nonconvergent']=True
    elif case=='task_churn':row['task_churn']=True
    elif case=='missing_final':row['unscanned_final_identities']=[[12,12,'22']]
    elif case=='passes':row['closure_passes']=6
    elif case=='duplicate':row['records'].append(copy.deepcopy(record))
    elif case=='unknown_record':record['identity']=[99,99,'99']
    with self.assertRaises(M.Error):M.validate_round(row,1,{(26,2)})

 def test_every_round_rejects_refs_denials_missing_proof_and_all_churn(self):
  row=self.round();M.validate_round(row,1,{(26,2)})
  for key,value in [('status','FAIL'),('round',2),('observer_sha256',M.PREDECESSOR_SHA),('baseline_sha256','0'*64),('scan_complete',False),('task_churn',True),('closure_nonconvergent',True),('records',[]),('censuses',[])]+[(k,[{}]) for k in ('path_failures_before','path_failures_after','target_references','permission_denials','incomplete','identity_replacements','entry_churn','unscanned_final_identities')]:
   with self.subTest(key=key):
    modified=copy.deepcopy(row);modified[key]=value
    with self.assertRaises(M.Error):M.validate_round(modified,1,{(26,2)})
  modified=copy.deepcopy(row);modified['records'][0]['mount_proof']['complete']=False
  with self.assertRaises(M.Error):M.validate_round(modified,1,{(26,2)})

 def test_inventory_noatime_determinism_and_archive_exact_comparison(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);names=sorted(set(M.SPECIAL)|{'file-%02d'%i for i in range(19)})
   contents={name:b'x' for name in names};contents[names[0]]=b'y'*(10826817-23)
   for name,data in contents.items():(root/name).write_bytes(data)
   fd=M.open_directory(root)
   try:first,identities=M.source_inventory(fd);second,second_ids=M.source_inventory(fd)
   finally:os.close(fd)
   self.assertEqual(first,second);self.assertEqual(identities,second_ids)
   archive=io.BytesIO()
   with tarfile.open(fileobj=archive,mode='w',format=tarfile.PAX_FORMAT) as tar:
    for row in first:
     info=tarfile.TarInfo('././'+row['path']);info.uid=row['uid'];info.gid=row['gid'];info.mode=row['mode'];info.pax_headers={'mtime':str(Decimal(row['mtime_ns'])/Decimal(1000000000))}
     if row['type']=='directory':info.type=tarfile.DIRTYPE;tar.addfile(info)
     else:info.size=row['size'];tar.addfile(info,io.BytesIO(contents[row['path']]))
   archived=M.archive_inventory(archive.getvalue());self.assertEqual(first,archived)
   expected_special={name:M.digest(contents[name]) for name in M.SPECIAL}
   with mock.patch.object(M,'COMPARABLE_SHA',M.digest(M.encoded(first))),mock.patch.object(M,'LIVE_IDENTITY_SHA',M.digest(M.encoded(identities))),mock.patch.object(M,'SPECIAL',expected_special):
    M.validate_original_inventory(second,second_ids,archived,prior=(first,identities))
    # Historical identity cannot substitute for the exact current binding.
    with mock.patch.object(M,'IDENTITY_SHA',M.LIVE_IDENTITY_SHA),mock.patch.object(M,'LIVE_IDENTITY_SHA','0'*64):
     with self.assertRaisesRegex(M.Error,'inventory binding'):M.validate_original_inventory(first,identities,archived)
    changed=copy.deepcopy(archived);changed[-1]['sha256']='0'*64
    with self.assertRaises(M.Error):M.validate_original_inventory(first,identities,changed)
    changed_ids=copy.deepcopy(identities);changed_ids[1][1][-1]+=1
    with self.assertRaises(M.Error):M.validate_original_inventory(first,changed_ids,archived)
    # Even an independently accepted later identity must equal the first
    # snapshot throughout this invocation; no fresh snapshot resets admission.
    with mock.patch.object(M,'LIVE_IDENTITY_SHA',M.digest(M.encoded(changed_ids))):
     with self.assertRaisesRegex(M.Error,'changed across NOATIME snapshots'):
      M.validate_original_inventory(first,changed_ids,archived,prior=(first,identities))

 def test_archive_rejects_traversal_and_duplicate_normalized_paths(self):
  for names in (('../outside',),('./x','././x')):
   raw=io.BytesIO()
   with tarfile.open(fileobj=raw,mode='w') as archive:
    for name in names:
     info=tarfile.TarInfo(name);info.size=1;archive.addfile(info,io.BytesIO(b'x'))
   with self.assertRaises(M.Error):M.archive_inventory(raw.getvalue())

 def test_prior_failure_inventory_exact_archive_and_stable_noatime(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);names=sorted(M.PRIOR_SPECIAL)
   contents={name:b'x' for name in names};contents[names[0]]=b'y'*(2362404-2)
   for name,data in contents.items():(root/name).write_bytes(data)
   fd=M.open_directory(root)
   try:rows,ids=M.source_inventory(fd);again,againids=M.source_inventory(fd)
   finally:os.close(fd)
   archive=io.BytesIO()
   with tarfile.open(fileobj=archive,mode='w',format=tarfile.PAX_FORMAT) as tar:
    for row in rows:
     info=tarfile.TarInfo('./'+row['path']);info.uid=row['uid'];info.gid=row['gid'];info.mode=row['mode'];info.pax_headers={'mtime':str(Decimal(row['mtime_ns'])/Decimal(1000000000))}
     if row['type']=='directory':info.type=tarfile.DIRTYPE;tar.addfile(info)
     else:info.size=row['size'];tar.addfile(info,io.BytesIO(contents[row['path']]))
   archived=M.archive_inventory(archive.getvalue())
   with mock.patch.object(M,'PRIOR_COMPARABLE_SHA',M.digest(M.encoded(rows))),mock.patch.object(M,'PRIOR_IDENTITY_SHA',M.digest(M.encoded(ids))),mock.patch.object(M,'PRIOR_SPECIAL',{name:M.digest(data) for name,data in contents.items()}):
    M.validate_prior_inventory(again,againids,archived,prior=(rows,ids))
    for case in ('count','hash','archive','identity','snapshot'):
     with self.subTest(case=case):
      changed,changedids,changedarchive=copy.deepcopy((rows,ids,archived))
      if case=='count':changed.pop()
      elif case=='hash':changed[-1]['sha256']='0'*64
      elif case=='archive':changedarchive[-1]['sha256']='0'*64
      else:changedids[1][1][-1]+=1
      if case=='snapshot':
       with mock.patch.object(M,'PRIOR_IDENTITY_SHA',M.digest(M.encoded(changedids))):
        with self.assertRaisesRegex(M.Error,'changed across NOATIME snapshots'):M.validate_prior_inventory(changed,changedids,changedarchive,prior=(rows,ids))
      else:
       with self.assertRaises(M.Error):M.validate_prior_inventory(changed,changedids,changedarchive,prior=(rows,ids))

if __name__=='__main__':unittest.main()
