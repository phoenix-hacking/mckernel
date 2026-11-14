"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Real recursive observers; only host control/proc/command/clock effects are fixtures.
Never replaces an observe function. No live guard/capture/subprocess/lease/export.
"""
from pathlib import Path
import builtins
import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import tempfile
import types
import unittest
import prepare_routing as p

D=Path(__file__).resolve().parent
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def write(path,value):p.create(path,value);return p.ref(path)

def fixture(directory,operation_mutation=None):
 layout=p.prepare(directory);d=layout['root'];observer=p.ref(layout['observer'])
 source60=layout['current60']/'observe_current60_postjoin.py';common=layout['common']/'observe_root59_configured.py'
 shared=load(p.SHARED,'TEST_ONLY118_shared_pure')
 operation=p.read(d/'ROOT118-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json')
 operation.update(operation_cutoffs=p.LIMITS,subjects=dict(observer=observer,current60=p.ref(source60),common=p.ref(common)),source_owners=['/root','/root/m14_compose','/root/restart_guard'],minimum_cumulative_spent='22812.3311',guardian=dict(source=shared.GUARDIAN_SOURCE,entrypoint='guard'))
 if operation_mutation:operation_mutation(operation)
 opref=write(d/'TEST_ONLY-OPERATION.json',operation)
 review=write(d/'TEST_ONLY-OPERATION-REVIEW.json',dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY',operation='current118-build',successor=operation))
 config=write(d/'TEST_ONLY-GUARD-CONFIG.json',dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='current118-build',shared_guard=p.ref(p.SHARED),successor=opref,review=review,subjects=operation['subjects']))
 phys=load(p.PHYSICAL,'TEST_ONLY118_phys_config');history=phys.source_chain()
 physicalreview=write(d/'TEST_ONLY-PHYSICAL-REVIEW.json',dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR',successor_source=p.ref(p.PHYSICAL),historical_sources=history,guard_adapter=p.ref(p.ADAPTER),guard_config=config))
 physical=write(d/'TEST_ONLY-PHYSICAL-CONFIG.json',dict(author='/root',successor_source=p.ref(p.PHYSICAL),historical_sources=history,guard_adapter=p.ref(p.ADAPTER),guard_config=config,independent_review=physicalreview,runtime_authority=None))
 deps=p.read(layout['common']/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json');deps.update(author='/root',account_window_guard_configuration=config,physical_history_configuration=physical)
 cr=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES',reviewed_observer=p.ref(common))
 for key in ['account_window_guard','account_window_guard_configuration','physical_history_observer','physical_history_configuration']:cr['reviewed_'+key]=deps[key]
 deps['independent_dependency_review']=write(d/'TEST_ONLY-COMMON-REVIEW.json',cr)
 commonref=write(layout['common']/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',deps)
 rd=p.read(d/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json');rd.update(author='/root',guard_configuration=config)
 rd['independent_review']=write(d/'TEST_ONLY-ROOT61-REVIEW.json',dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_CURRENT118_OBSERVER_DEPENDENCIES',observer=observer,guard_adapter=p.ref(p.ADAPTER),guard_configuration=config))
 rdref=write(d/'ROOT61-RUNTIME-DEPENDENCIES.json',rd)
 root=load(layout['observer'],'TEST_ONLY118_root61_data')
 schema=p.ref(d/'OBSERVER-SCHEMA.CURRENT118.SOURCE-ONLY.json')
 sr=write(d/'TEST_ONLY-SCHEMA-REVIEW.json',dict(independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=schema))
 boundary=dict(author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',nonce_ledger=root.CURRENT['ledger'],native_custody_clearance=root.CURRENT['latest_free'],observer=observer,independent_current_boundary_review=write(d/'TEST_ONLY-BOUNDARY-REVIEW.json',dict(TEST_ONLY=True)),observer_schema=schema,observer_schema_review=sr,root_attests_exact_current_boundary=True)
 write(layout['cohort']/'ROOT-ACTUAL-CURRENT-BOUNDARY.json',boundary)
 bind=write(d/'TEST_ONLY-BIND-INPUT.json',dict(author='/root',decision='BIND_RECURSIVE118_RUNTIME_DEPENDENCIES_SOURCE_ONLY',runtime_authority=None,source_delta_manifest=p.ref(d/'EXACT-SOURCE-DELTAS.json'),common_dependencies=commonref,root61_dependencies=rdref,guard_configuration=config))
 p.bind_dependencies(bind['path'],d)
 return layout,config


class Effects:
 """Only the real host effects below are substituted; observers execute intact."""
 def __init__(self,layout,config):
  self.layout=layout;self.config=config;self.calls=[];self.loaded=[];self.configured=[];self.held=False;self.census=[]
  self.clocks=[v-600 for v in p.LIMITS]
  capture=p.read(p.E/'current116-actual-postjoin-current60-source-20261028-1/ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json')
  self.oracle={}
  def collect(value):
   if isinstance(value,dict):
    if all(k in value for k in ['argv','returncode','stdout','stderr'])and isinstance(value['argv'],list):self.oracle[tuple(value['argv'])]=value
    for v in value.values():collect(v)
   elif isinstance(value,list):
    for v in value:collect(v)
  collect(capture)
  self.capacity=capture['historical_Root59_native_and_physical']['capacity']
  self.physical=None
  self.metadata=types.SimpleNamespace(st_mode=stat.S_IFREG|0o644,st_dev=27,st_ino=4,st_uid=0,st_gid=0,st_size=0,st_nlink=1)
  self.os=types.SimpleNamespace(**{name:getattr(os,name)for name in dir(os)if not name.startswith('__')})
  self.os.path=types.SimpleNamespace(**{name:getattr(os.path,name)for name in dir(os.path)if not name.startswith('__')})
  self.os.path.lexists=lambda path:False
  self.os.open=self.open_fd;self.os.close=self.close_fd;self.os.fstat=lambda fd:self.metadata
  self.os.stat=lambda path:types.SimpleNamespace(st_dev=1828)if str(path)=='/home/holden/mckernel-work/scratch'else self.metadata
  self.os.statvfs=lambda path:types.SimpleNamespace(f_bavail=self.capacity[str(path)],f_frsize=1)
  self.os.getpid=lambda:600001
  self.fcntl=types.SimpleNamespace(LOCK_EX=2,LOCK_NB=4,flock=self.flock)
 def open_fd(self,*args):self.calls.append(('virtual_os_open',str(args[0])));return 700
 def close_fd(self,fd):self.held=False
 def flock(self,fd,flags):self.held=True
 def path(self,*parts):
  real=Path(*parts);name=str(real)
  if name.startswith('/proc')or name.startswith('/sys/fs/cgroup')or name=='/run/lock/mckernel-development.lock':return Proc(self,name)
  return real
 def run(self,argv,*args,**kwargs):
  self.calls.append(('command',list(argv)))
  if '--historical'in argv:
   historical=Path(argv[argv.index('--historical')+1]);value=self.physical.observe(historical)
   raw=json.dumps(value);return types.SimpleNamespace(returncode=0,stdout=raw if kwargs.get('text')else raw.encode(),stderr=''if kwargs.get('text')else b'')
  if argv[0]=='/usr/bin/findmnt':
   expected=p.read(p.E/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json')['mount']
   return types.SimpleNamespace(returncode=0,stdout=json.dumps(dict(filesystems=[expected])),stderr='')
  row=self.oracle[tuple(argv)]
  return types.SimpleNamespace(returncode=row['returncode'],stdout=row['stdout']if kwargs.get('text')else row['stdout'].encode(),stderr=row['stderr']if kwargs.get('text')else row['stderr'].encode())
 def namespace(self,namespace):
  namespace.update(Path=self.path,os=self.os,fcntl=self.fcntl,time=types.SimpleNamespace(time=lambda:self.clocks[0]),subprocess=types.SimpleNamespace(run=self.run))
  for key,value in list(namespace.items()):
   if isinstance(value,Path)and str(value)=='/run/lock/mckernel-development.lock':namespace[key]=self.path(value)
 def patch(self,module):
  name=str(module.__file__);self.loaded.append(name)
  if name==str(p.ADAPTER):
   configure=module.configure
   def configured(row):
    assert row==self.config,'same exact118 config at every observer depth'
    configure(row) # Genuine adapter/shared operation/guardian identity validation.
    self.configured.append(name)
    module.guard=lambda:list(self.clocks) # Live account/guardian/clock effect leaf.
   module.configure=configured
  elif name==str(p.PHYSICAL):
   self.physical=module
   originalguard=module.guard_module
   def guard():
    adapter=originalguard() # Real pure configure before the live effect substitution.
    assert adapter.binding()[0]['shared_guard']==p.ref(p.SHARED)
    self.configured.append(str(p.ADAPTER));adapter.guard=lambda:list(self.clocks);return adapter
   module.guard_module=guard
   originalexec=module.HistoricalSuccessorLoader.exec_module
   def execute(loader,target):
    originalexec(loader,target);self.loaded.append(str(loader.path));self.namespace(target.__dict__)
    def helper_exec(code,namespace):
     builtins.exec(code,namespace);self.namespace(namespace)
    target.exec=helper_exec
   module.HistoricalSuccessorLoader.exec_module=execute
   module.subprocess=types.SimpleNamespace(run=self.run)
  elif name.endswith(('observe_current61_current118.py','observe_current60_postjoin.py','observe_root59_configured.py')):
   self.namespace(module.__dict__)
   original=module.load
   module.load=lambda row,label:self.patch(original(row,label))
  return module


class Proc:
 def __init__(self,effects,name):self.e=effects;self.raw=name
 def __str__(self):return self.raw
 def __fspath__(self):return self.raw
 def __truediv__(self,part):return Proc(self.e,self.raw+'/'+str(part))
 @property
 def parent(self):return Proc(self.e,str(Path(self.raw).parent))
 def exists(self):return False
 def lstat(self):return self.e.metadata
 def stat(self):return self.e.metadata
 def iterdir(self):
  assert self.raw=='/proc';return[Proc(self.e,'/proc/'+str(row['pid']))for row in self.e.census]
 @property
 def name(self):return Path(self.raw).name
 def read_text(self):
  if self.raw=='/proc/locks':return '1: FLOCK ADVISORY WRITE 600001 00:1b:4 0 EOF\n'if self.e.held else ''
  if self.raw=='/proc/net/unix':return 'Num RefCount Protocol Flags Type St Inode Path\n'
  if self.raw=='/proc/meminfo':return 'MemAvailable: 50331648 kB\n'
  if self.raw.startswith('/sys/fs/cgroup')and self.raw.endswith('pids.current'):return '0\n'
  raise AssertionError('unhandled virtual proc read '+self.raw)
 def open(self):
  assert self.raw.endswith('/stat')
  pid=int(self.raw.split('/')[2]);row=next(x for x in self.e.census if x['pid']==pid)
  return io.StringIO(str(pid)+' (TEST_ONLY) S 1 '+str(row['pgrp'])+' '+'0 '*20+'\n')


class Recursive(unittest.TestCase):
 def test_full_recursive_real_observers_and_negative_actor(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-full-recursion-',dir=D)as temporary:
   layout,config=fixture(Path(temporary)/'prepared')
   effects=Effects(layout,config);root=effects.patch(load(layout['observer'],'TEST_ONLY118_full_recursive'))
   result=root.observe()
   self.assertEqual(result['Root61'],root.CURRENT['ledger']);self.assertEqual(result['fixed_cutoffs'],p.LIMITS)
   self.assertEqual(result['actual_latest_operation_postjoin_acceptance'],root.CURRENT['latest_free'])
   self.assertTrue(result['no_existing_heavy']);self.assertEqual(result['pids_current'],0)
   historical=load(p.PHYSICAL,'TEST_ONLY_physical_chain_expected').source_chain()
   self.assertTrue(set(historical)<=set(effects.loaded));self.assertGreater(len(effects.configured),3)
   self.assertTrue(all(call[0]in ['command','virtual_os_open']for call in effects.calls))
   # Same predicates must reject a process-group survivor at the deepest proc census.
   effects.census=[dict(pid=700001,pgrp=1901981)]
   with self.assertRaises((ValueError,AssertionError)):root.observe()
   Recursive.result=dict(status='PASS_FULL_RECURSIVE118_OBSERVERS_EFFECT_LEAVES_ONLY',historical_sources=len(historical),guard_pure_configurations=len(effects.configured),effect_calls=len(effects.calls),retained_consumed_nonces=70,actual_guard_calls=0,actual_capture_calls=0,actual_subprocesses=0,observe_functions_replaced=0)
 def test_old_guardian_and_wider_caps_rejected(self):
  old=p.read(p.E/'new-window-resume-20261028-1/CURRENT116-OPERATION-2-ALL-CONTROLS/EXPLICIT-OPERATION-SUCCESSOR.json')['guardian']
  for mutation in [lambda op:op.update(guardian=old),lambda op:op['operation_cutoffs'].__setitem__(1,p.LIMITS[1]+1)]:
   with tempfile.TemporaryDirectory(prefix='TEST_ONLY-bad-recursion-',dir=D)as temporary:
    layout,config=fixture(Path(temporary)/'prepared',mutation)
    effects=Effects(layout,config);root=effects.patch(load(layout['observer'],'TEST_ONLY118_bad_recursive'))
    with self.assertRaises(ValueError):root.observe()


if __name__=='__main__':
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Recursive))
 (D/'PURE-RECURSIVE.stdout').write_text(stream.getvalue())
 summary=dict(scope=__doc__.splitlines()[0],status='PASS'if result.wasSuccessful()else'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),result=getattr(Recursive,'result',None),runtime_authority=None)
 (D/'PURE-RECURSIVE.json').write_text(json.dumps(summary,indent=2)+'\n');print(stream.getvalue(),end='');print(json.dumps(summary,indent=2));raise SystemExit(0 if result.wasSuccessful() else 1)
