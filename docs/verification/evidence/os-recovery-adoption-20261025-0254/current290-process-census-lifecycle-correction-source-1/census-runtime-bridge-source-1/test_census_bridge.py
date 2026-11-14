"""Functional exact namespace bridge tests; no security testing/runtime actions.
A genuine virtual e49 module is compiled from authenticated old bytes; old
configure/root/query/Transaction are never executed. Retained release globals
are supplied as fixture context. Full14 collector fixtures also run bridged.
"""
import copy,hashlib,importlib.util,json,sys,types,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('exact_census_bridge',ROOT/'census_runtime_bridge.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def old_engine():
 ref=b.FROZEN_INPUTS['baseline'];raw=b.authenticated(ref);m=types.ModuleType('virtual_original_e49');m.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),m.__dict__)
 release=json.loads(b.authenticated(b.FROZEN_INPUTS['old_release']));m.RELEASE=release;m.BOOT_ID=release['observation']['boot_id'];m.OWNER_PID=release['observation']['target']['owner_pid'];m.WAITER_PIDS=tuple(row['pid'] for row in release['observation']['client_ledger']);m._process_report=object();m.CENSUS_DELTA_BOUND=False
 return m
class Checks(unittest.TestCase):
 def test_exact_three_slots_and_context_preserved(self):
  m=old_engine();before=dict(m.__dict__);release_bytes=b.canonical(m.RELEASE);manifest=b.install_census_delta(m,b.expected_authorization())
  self.assertEqual(manifest['changed_slots'],list(b.SLOTS));self.assertEqual(m.__file__,before['__file__']);self.assertEqual(m.PUBLISHED_SCRIPT,before['PUBLISHED_SCRIPT']);self.assertIs(m.RELEASE,before['RELEASE']);self.assertEqual(b.canonical(m.RELEASE),release_bytes)
  for name,value in before.items():
   if name not in b.SLOTS:self.assertIs(m.__dict__[name],value,name)
  self.assertEqual(set(m.__dict__)-set(before),{b.MANIFEST_SLOT})
  for name in b.SLOTS[1:]:self.assertEqual(m.__dict__[name].__code__.co_filename,b.FROZEN_INPUTS['corrected']['path']);self.assertIs(m.__dict__[name].__globals__,m.__dict__)
 def test_strict_new_report_pass_old_schema_rejected(self):
  m=old_engine();b.install_census_delta(m,b.expected_authorization());caller=[888,'555'];report=dict(schema='fp-save-image.proc.lifecycle.v2',uid=0,boot_id=m.BOOT_ID,challenge='fixture',caller=caller,publishers=[],snapshots=[[[1,0,'1'],[888,1,'555']]]*2,attempts=1,retry_failures=[])
  m.validate_process_report(report,'fixture',caller)
  report['schema']='fp-save-image.proc.v1'
  with self.assertRaises(m.Refusal):m.validate_process_report(report,'fixture',caller)
 def test_wrong_authority_unapproved_slots_reinstall_refuse(self):
  for mutate in [lambda a:a.update(author='other'),lambda a:a.update(corrected_source_sha256='0'*64),lambda a:a.update(old_plan_sha256='0'*64)]:
   m=old_engine();before=dict(m.__dict__);auth=b.expected_authorization();mutate(auth)
   with self.assertRaises(b.BridgeRefusal):b.install_census_delta(m,auth)
   for name,value in before.items():self.assertIs(m.__dict__[name],value)
  m=old_engine()
  with self.assertRaisesRegex(b.BridgeRefusal,'unapproved-delta-slots'):b.install_census_delta(m,b.expected_authorization(),slots=('PROC_CODE','recover'))
  b.install_census_delta(m,b.expected_authorization())
  with self.assertRaises(b.BridgeRefusal):b.install_census_delta(m,b.expected_authorization())
 def test_modified_baseline_missing_dependency_or_wrong_file_refuse(self):
  for mutate in [lambda m:setattr(m,'process_absent',lambda:None),lambda m:setattr(m,'run_privileged',lambda args:None),lambda m:setattr(m,'PROC_CODE','modified'),lambda m:setattr(m,'__file__',b.FROZEN_INPUTS['corrected']['path']),lambda m:setattr(m,'PUBLISHED_SCRIPT','wrong'),lambda m:m.__dict__.pop('json')]:
   m=old_engine();mutate(m);before=dict(m.__dict__)
   with self.assertRaises(b.BridgeRefusal):b.install_census_delta(m,b.expected_authorization())
   for name,value in before.items():self.assertIs(m.__dict__[name],value)
 def test_wrong_source_bytes_fail_before_install(self):
  m=old_engine();wrong=ROOT/'WRONG-SOURCE-FIXTURE.py';wrong.write_bytes(b'# deliberately mismatched own fixture bytes\n')
  altered=dict(b.FROZEN_INPUTS['corrected'],path=str(wrong))
  with mock.patch.dict(b.FROZEN_INPUTS,{'corrected':altered}):
   with self.assertRaisesRegex(b.BridgeRefusal,'exact-source-bytes'):b.install_census_delta(m,b.expected_authorization())
  self.assertNotIn(b.MANIFEST_SLOT,m.__dict__)
 def test_all_fourteen_collector_fixtures_with_genuine_bridged_consumer(self):
  m=old_engine();b.install_census_delta(m,b.expected_authorization());path=ROOT.parent/'test_lifecycle.py';raw=path.read_text()
  # Bind only fixture owner/client numbers to this genuine retained oldrelease;
  # production collector/validator bodies remain byte-for-byte unchanged.
  raw=raw.replace('assertRaisesRegex(RuntimeError,','assertRaisesRegex(ValueError,').replace('with self.assertRaises(RuntimeError):validate','with self.assertRaises(ValueError):validate');raw=raw.replace('OWNER_PID=9000','OWNER_PID='+str(m.OWNER_PID)).replace('WAITER_PIDS=(9001,)','WAITER_PIDS=('+str(m.WAITER_PIDS[0])+',)').replace('FS([[1,99,9000]]*2)','FS([[1,99,'+str(m.OWNER_PID)+']]*2)')
  ns={'__name__':'bridge_compatibility_fixture','__file__':str(path)};exec(compile(raw,str(path),'exec'),ns);ns['BOOT']=m.BOOT_ID;ns['NEW']=m.PROC_CODE
  def validate(report):m.validate_process_report(report,ns['CHALLENGE'],ns['CALLER']);return True
  ns['validate']=validate
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(ns['Checks']);result=unittest.TestResult();suite.run(result)
  self.assertEqual(result.testsRun,14);self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
  (ROOT/'FOURTEEN-BRIDGED-FIXTURE-RESULT.json').write_text(json.dumps(dict(tests=result.testsRun,errors=0,failures=0,collector_source_sha256=b.FROZEN_INPUTS['corrected']['sha256'],bridge_manifest=m.__dict__[b.MANIFEST_SLOT],fixture_owner=m.OWNER_PID,fixture_boot=m.BOOT_ID,scope='virtual old e49 module; bridged genuine consumer+PROC_CODE; all procfs mocked; no runtime'),indent=2)+'\n')
if __name__=='__main__':unittest.main(verbosity=2)
