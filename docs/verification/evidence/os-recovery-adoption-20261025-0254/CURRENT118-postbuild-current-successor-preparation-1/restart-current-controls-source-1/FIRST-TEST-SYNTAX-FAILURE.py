"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused semantic source binding tests; no runtime modules or effect leaves execute.
"""
import ast
import copy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
import prepare_current_controls as m

class SourceBindings(unittest.TestCase):
    def test_shared_guard_only_two_assignments_change(self):
        raw=m.PINS['shared_guard'][0].read_text()
        guardian={'path':'/TEST_ONLY/guardian.py','bytes':10,'sha256':'1'*64}
        changed=m.rewrite_guard(raw,guardian,'TEST_ONLY_new_thread')
        old=ast.parse(raw);new=ast.parse(changed)
        assignments=lambda t:{n.targets[0].id:ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in ('GUARDIAN_SOURCE','THREAD','CUTOFFS','OPERATION_CUTOFFS','BOOT','RUN','CEILING','WINDOW_SHA256')}
        a=assignments(old);b=assignments(new)
        self.assertEqual(b['GUARDIAN_SOURCE'],guardian);self.assertEqual(b['THREAD'],'TEST_ONLY_new_thread')
        self.assertEqual({k:v for k,v in a.items()if k not in ('THREAD','GUARDIAN_SOURCE')},{k:v for k,v in b.items()if k not in ('THREAD','GUARDIAN_SOURCE')})
        fns=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(fns(old),fns(new))
    def test_missing_guardian_assignment_rejected(self):
        raw=m.PINS['shared_guard'][0].read_text()
        with self.assertRaises(ValueError):m.rewrite_guard(raw.replace('GUARDIAN_SOURCE =','WRONG_SOURCE ='),{},'TEST_ONLY')
    def test_missing_actual_controls_manifest_is_not_materialization(self):
        with self.assertRaises(ValueError):m.validate_manifest({'schema':'mckernel.current118.postjoin-control-source-inputs.v1'}, {})
        self.assertFalse((m.HERE/'observe_current64_current118_postjoin.py').exists())
    def test_review_must_bind_exact_new_source(self):
        row={'path':'/TEST_ONLY/guardian.py','bytes':2,'sha256':'a'*64}
        good={'TEST_ONLY':True,'independent':True,'implementation_ownership':False,'decision':'PASS_TEST_ONLY_SOURCE','sources':{'guardian':row}}
        m.review_binds(good,[row])
        for update in [{'independent':False},{'implementation_ownership':True},{'decision':'PENDING'},{'sources':{'guardian':dict(row,sha256='b'*64)}}]:
            bad=dict(good,**update)
            with self.assertRaises(ValueError):m.review_binds(bad,[row])
    def test_cleanup_mechanical_successor_and_stale_runtime_ref_rejected(self):
        pins=json.loads(m.PINS['inputs'][0].read_bytes())
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-control-binding-',dir=m.HERE)as name:
            root=Path(name)
            def put(name,value):
                p=root/name;p.write_text(json.dumps(value,indent=2)+'\n'if not isinstance(value,str)else value);return m.ref(p)
            guardian=put('guardian.py','def guard():\n    raise AssertionError("TEST_ONLY never executed")\n')
            b=m.checked(pins['retirement_bindings']);b['guardian']=guardian;b['output_root_parent']=str(root)
            br=put('BINDINGS.json',b)
            code=m.auth(pins['retirement_source']).read_text().replace(pins['retirement_bindings']['sha256'],br['sha256'])
            er=put('retire_exact_current118_stopped_container.py',code)
            runtime=m.checked(pins['compatibility_runtime_files']);runtime.update(executor=er,bindings=br,guardian=guardian)
            rr=put('RUNTIME-FILES.json',runtime)
            sr=put('SOURCE_READY.json',{'TEST_ONLY':True,'runtime_files':rr})
            review=put('REVIEW.json',{'TEST_ONLY':True,'independent':True,'implementation_ownership':False,'decision':'PASS_TEST_ONLY_SOURCE','files':[er,br,rr]})
            manifest=dict(guardian=guardian,cleanup_executor=er,cleanup_bindings=br,cleanup_runtime_files=rr,cleanup_source_ready=sr,cleanup_source_review=review)
            m.validate_cleanup(pins,manifest)
            stale=dict(manifest,cleanup_runtime_files=pins['compatibility_runtime_files'])
            with self.assertRaises(ValueError):m.validate_cleanup(pins,stale)
            altered=copy.deepcopy(b);altered['cutoffs'][0]+=1;bad=dict(manifest,cleanup_bindings=put('BAD-BINDINGS.json',altered))
            with self.assertRaises(ValueError):m.validate_cleanup(pins,bad)
    def test_fixed_actual_custody_and_ledger_pins(self):
        refs={k:m.ref(p)for k,(p,digest)in m.PINS.items()}
        for key,(_,digest)in m.PINS.items():self.assertEqual(refs[key]['sha256'],digest)
        receipt=m.checked(refs['custody_validation'])
        self.assertEqual(receipt['custody_supplement'],refs['custody']);self.assertEqual(receipt['ledger'],refs['ledger'])
        self.assertEqual((receipt['historical_and_measured_actors'],receipt['consumed_nonces']),(128,72))
        self.assertEqual(receipt['old_readonly_client_status'],'UNKNOWN');self.assertFalse(receipt['current_free'])

if __name__=='__main__':
    start=time.monotonic();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SourceBindings))
    (m.HERE/'PURE-SOURCE-BINDINGS.stdout').write_text(stream.getvalue())
    summary=dict(scope=m.SCOPE,status='PASS'if result.wasSuccessful()else'FAIL',groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,compiler_guard_cleanup_proc_capture_calls=0,materialized_successor=False,runtime_authority=None)
    (m.HERE/'PURE-SOURCE-BINDINGS.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(stream.getvalue(),end='');print(json.dumps(summary));raise SystemExit(0 if result.wasSuccessful()else1)
