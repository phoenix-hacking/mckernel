"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute real Root62 census and every inherited observer. Substitute effect leaves
only, using authenticated retained replies and the owner's complete result oracle.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import types
import unittest
import uuid

import observe_current62_bfd_postjoin as source
import test_retirement_adoption as adoption

D=Path(__file__).resolve().parent
EXPERT=Path(source.PINS['prior_ledger']['path']).parent.parent/'m14-next118-recursive-fixture-expert-20261028-1'

def pinned_load(path,name,sha):
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

oracle=pinned_load(EXPERT/'actual-bfd-physical-input-supplement-1/retained_effect_oracle.py','retained_effect_oracle','3ff77a9c681a6a733ed9a86a5d669302d954b6002522b5cde0ff5d6fe36f29b4')
saved=sys.modules.get('retained_effect_oracle');sys.modules['retained_effect_oracle']=oracle
try:expert=pinned_load(EXPERT/'test_recursive_routing_expert.py','source_bound_existing_effect_leaves','b9e27a5dce71310a943d393688153cdb72cbf191959f5b556bd16450ac17661a')
finally:
 if saved is None:sys.modules.pop('retained_effect_oracle',None)
 else:sys.modules['retained_effect_oracle']=saved

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def write(path,value):
 path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(value,indent=2)+'\n');return source.ref(path)

def fixture(root,mutation=None):
 """Copy only the exact candidate source closure; all Root data is TEST_ONLY."""
 root.mkdir()
 names=['observe_current62_bfd_postjoin.py','bind_history.py','INPUTS.json','ROOT62-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json','OBSERVER-SCHEMA.ROOT63-CURRENT.SOURCE-ONLY.json']
 names.extend(str(path.relative_to(D))for path in (D/'history').iterdir()if path.suffix in ('.py','.json')and 'TEMPLATE' in path.name or path.suffix=='.py'and path.parent==D/'history')
 for name in names:
  dest=root/name;dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes((D/name).read_bytes())
 p=root/'history/observe_bfd_current61.py';p.write_text(p.read_text().replace(str(D/'history/observe_bfd_current60_history.py'),str(root/'history/observe_bfd_current60_history.py')))
 def reroute(value):
  if isinstance(value,dict):
   if set(value)=={'path','bytes','sha256'}and value['path'].startswith(str(D)+'/'):
    q=root/Path(value['path']).relative_to(D)
    if q.is_file():return source.ref(q)
   return {key:reroute(child)for key,child in value.items()}
  if isinstance(value,list):return [reroute(child)for child in value]
  return value
 for path in root.rglob('*.json'):write(path,reroute(json.loads(path.read_bytes())))
 m=load(root/'observe_current62_bfd_postjoin.py','TEST_ONLY_real_current62_observer')
 oldm,oldd=adoption.m,adoption.D;adoption.m=m;adoption.D=root
 retirement_dir=root/'TEST_ONLY-retirement';retirement_dir.mkdir()
 try:f=adoption.future_fixture(retirement_dir)
 finally:adoption.m=oldm;adoption.D=oldd
 shared=load(Path(m.PINS['shared_guard']['path']),'TEST_ONLY_pure62operation')
 op=json.loads((Path(m.PINS['shared_guard']['path']).parent/'ROOT62-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
 op.update(author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',subjects=m.source_subjects(),source_owners=['/root','/root/m14_compose','/root/bfd_route','/root/restart_guard'],minimum_cumulative_spent='22812.3311')
 if mutation:mutation(op)
 opref=write(root/'TEST_ONLY-operation.json',op)
 review=write(root/'TEST_ONLY-operation-review.json',dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY',operation=m.PINS['new_operation'],successor=op))
 config=write(root/'TEST_ONLY-config.json',dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation=m.PINS['new_operation'],shared_guard=m.PINS['shared_guard'],successor=opref,review=review,subjects=op['subjects']))
 common=json.loads((root/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
 phys=load(Path(common['physical_history_observer']['path']),'TEST_ONLY_real_physical_source_chain')
 pr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR',successor_source=common['physical_history_observer'],historical_sources=phys.source_chain(),guard_adapter=m.PINS['guard_adapter'],guard_config=config)
 physical=write(root/'TEST_ONLY-physical.json',dict(author='/root',runtime_authority=None,**{k:pr[k]for k in ['successor_source','historical_sources','guard_adapter','guard_config']},independent_review=write(root/'TEST_ONLY-physical-review.json',pr)))
 common.update(author='/root',account_window_guard_configuration=config,physical_history_configuration=physical)
 cr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES',reviewed_observer=common['observer'])
 for key in ['account_window_guard','account_window_guard_configuration','physical_history_observer','physical_history_configuration']:cr['reviewed_'+key]=common[key]
 common['independent_dependency_review']=write(root/'TEST_ONLY-common-review.json',cr)
 commonref=write(root/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',common)
 top=json.loads((root/'history/ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json').read_bytes());top.update(author='/root',guard_configuration=config)
 tr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_BFD_OBSERVER_DEPENDENCIES',observer=top['observer'],guard_adapter=m.PINS['guard_adapter'],guard_configuration=config)
 top['independent_review']=write(root/'TEST_ONLY-history61-review.json',tr);write(root/'history/ROOT61-RUNTIME-DEPENDENCIES.json',top)
 pins=json.loads((root/'history/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json').read_bytes());pins['common_dependencies']=commonref;write(root/'history/ACTUAL-PINS.json',pins)
 bindings=dict(author='/root',decision='BIND_EXACT_ROOT62_BFD_POSTJOIN_OBSERVER',runtime_authority=None,phase='postjoin_candidate',ledger=f['pendingref'],retirement_result=f['retirement'],retirement_parent_join=f['retirement_join'],guard_adapter=m.PINS['guard_adapter'],guard_configuration=config)
 rr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT62_BFD_POSTJOIN_OBSERVER_DEPENDENCIES',observer=m.ref(m.__file__),phase='postjoin_candidate',capture_scope=m.capture_scope())
 for key in ['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration']:rr[key]=bindings[key]
 bindings['independent_review']=write(root/'TEST_ONLY-new-runtime-review.json',rr)
 return m,bindings,f,config,common['physical_history_observer']

class Effects(expert.Effects):
 def __init__(self,m,bindings,f,config,physical):
  expert.p=types.SimpleNamespace(LIMITS=m.PINS['limits'],PHYSICAL=Path(physical['path']),ADAPTER=Path(m.PINS['guard_adapter']['path']),SHARED=Path(m.PINS['shared_guard']['path']),ref=source.ref,create=write)
  super().__init__(dict(root=m.HERE),config)
  self.m=m;self.f=f;self.sequence=[];self.direct_clocks=list(self.clocks);self.new_commands=[];self.final_cutoff_read=False
  self.os.getpgrp=lambda:600001
 def patch(self,module):
  name=str(module.__file__)
  if name.endswith(('observe_current62_bfd_postjoin.py','observe_bfd_current61.py','observe_bfd_current60_history.py','observe_bfd_root59_history.py')):
   self.loaded.append(name);self.namespace(module.__dict__)
   module.time=types.SimpleNamespace(time=lambda:self.clock(0),monotonic=lambda:self.clock(1),CLOCK_BOOTTIME=7,clock_gettime=lambda which:self.clock(2))
   original=module.load;module.load=lambda row,label:self.patch(original(row,label));return module
  if name==self.m.PINS['retirement_executor']['path']:
   original=module.transport
   def transport(bindings):
    effects=self
    class Commands:
     client_retirement_unproven=False
     def __init__(self,out,stop):self.receipts=[];self.before_popen=None;self.out=out
     def exact(self,argv,timeout=30,check=True):
      self.before_popen(argv)
      effects.sequence.append('Popen-effect')
      return effects.command(self,argv)
    return Commands,types.SimpleNamespace(TEST_ONLY=True)
   module.transport=transport
   return module
  if name==self.f['executor'].bindings()['primitive']['path']:
   module.proc_stat=lambda pid:['0']*19+['200'];return module
  patched=super().patch(module)
  if name==self.m.PINS['guard_adapter']['path']:
   original=patched.current_cutoffs
   def cutoffs():
    self.sequence.append('configuration-I/O-effect')
    result=original()
    if self.final_cutoff_read is not False:
     index,value=self.final_cutoff_read;self.direct_clocks[index]=value
    return result
   patched.current_cutoffs=cutoffs
  return patched
 def clock(self,index):
  self.sequence.append(['direct-UTC','direct-MONO','direct-BOOT'][index]);return self.direct_clocks[index]
 def command(self,commands,argv):
  executor=self.f['executor'];b=executor.bindings();retirement=source.checked(self.f['retirement'])
  template=executor.authenticated(retirement['command_receipts'][0],True);index=len(commands.receipts)
  report=None
  if index in (0,4):
   assert argv[:6]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c']
   assert re.fullmatch('[0-9a-f]{32}',argv[7]);uuid.UUID(hex=argv[7]) # Real uuid API value, never a callable fake.
   report=copy.deepcopy(executor.authenticated(retirement['proofs'][-1],True)['process'])
   report.update(challenge=argv[7],caller=[600001,'200'])
   report['snapshots']=[[[1,0,'1'],[600001,1,'200']]]*2
   report['groups']=[[[1,0,'1',1,1],[600001,1,'200',600001,600001]]]*2
  else:assert argv==self.f['capture']['BFD_exact_absence_queries'][index-1]['argv']
  self.new_commands.append(list(argv))
  child=commands.out/('TEST_ONLY-command-'+str(index));child.mkdir()
  stdout=child/'stdout';stdout.write_text(json.dumps(report)if report is not None else'')
  stderr=child/'stderr';stderr.write_text('')
  pid=700100+index
  status=write(child/'status.json',dict(TEST_ONLY=True,state='exited',pid=pid,exit_code=0,argv=argv))
  row=copy.deepcopy(template);row.update(TEST_ONLY=True,pid=pid,birth=300+index,wait4_pid=pid,argv=argv,raw=dict(stdout=source.ref(stdout),stderr=source.ref(stderr),**{'status.json':status}))
  commands.receipts.append(write(child/'JOIN-WAIT4.json',row))
  return types.SimpleNamespace(returncode=0,stdout=stdout.read_text(),stderr='')

class ActualBodies(unittest.TestCase):
 def run_fixture(self,root,mutation=None):
  m,bindings,f,config,physical=fixture(root/'prepared',mutation)
  effects=Effects(m,bindings,f,config,physical);effects.patch(m)
  output=root/'TEST_ONLY-query-output';output.mkdir()
  return m,bindings,effects,output
 def test_real_recursive_observe_and_real_uuid_census(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-full-bodies-',dir=D)as directory:
   m,bindings,effects,out=self.run_fixture(Path(directory))
   result=m.observe(bindings,out)
   self.assertEqual(result['status'],m.STATUS);self.assertEqual(len(effects.new_commands),5)
   self.assertEqual(len(result['query_command_receipts']),5);self.assertTrue(result['unmeasured_producer_Docker_client_births'])
   m.validate_capture_commands(result)
   for index,item in enumerate(effects.sequence):
    if item=='Popen-effect':self.assertEqual(effects.sequence[index-3:index],['direct-UTC','direct-MONO','direct-BOOT'])
   self.assertGreater(len(effects.loaded),12);self.assertGreater(len([c for c in effects.calls if c[0]=='command']),5)
   ActualBodies.summary=dict(inherited_command_effects=len([c for c in effects.calls if c[0]=='command']),new_tracked_commands=5,loaded_sources=len(set(effects.loaded)),observe_functions_replaced=0,actual_effects=0)
 def test_stale_final_direct_clock_blocks_before_first_new_spawn(self):
  vectors=[(index,source.PINS['limits'][index])for index in range(3)]+[(1,source.PINS['limits'][1]-480),(1,source.PINS['limits'][1]-601)]
  for vector in vectors:
   with tempfile.TemporaryDirectory(prefix='TEST_ONLY-final-clock-',dir=D)as directory:
    m,bindings,effects,out=self.run_fixture(Path(directory));effects.final_cutoff_read=vector
    with self.assertRaisesRegex(ValueError,'final direct UTC/MONO/BOOT'):m.observe(bindings,out)
    self.assertEqual(effects.new_commands,[])
 def test_full_recursive_old_guardian_wider_cap_and_live_actor_rejected(self):
  old=json.loads((EXPERT.parent/'new-window-resume-20261028-1/CURRENT116-OPERATION-2-ALL-CONTROLS/EXPLICIT-OPERATION-SUCCESSOR.json').read_bytes())['guardian']
  for mutation in [lambda op:op.update(guardian=old),lambda op:op['operation_cutoffs'].__setitem__(1,source.PINS['limits'][1]+1)]:
   with tempfile.TemporaryDirectory(prefix='TEST_ONLY-bad-recursion-',dir=D)as directory:
    m,bindings,effects,out=self.run_fixture(Path(directory),mutation)
    with self.assertRaises((ValueError,AssertionError)):m.observe(bindings,out)
    self.assertEqual(effects.new_commands,[])
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-inherited-survivor-',dir=D)as directory:
   m,bindings,effects,out=self.run_fixture(Path(directory));effects.census=[dict(pid=700001,pgrp=1901981)]
   with self.assertRaises((ValueError,AssertionError)):m.observe(bindings,out)
   self.assertEqual(effects.new_commands,[])

if __name__=='__main__':unittest.main(verbosity=2)
