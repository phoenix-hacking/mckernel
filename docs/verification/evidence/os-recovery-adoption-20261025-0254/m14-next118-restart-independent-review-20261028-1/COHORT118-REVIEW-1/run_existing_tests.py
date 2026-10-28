"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent existing pure source/pipeline checks. Temporary fixtures only.
"""
from pathlib import Path
import contextlib,datetime,hashlib,importlib.util,io,json,resource,tempfile,types,unittest
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
HERE=Path(__file__).resolve().parent
PACKET=HERE.parent.parent/'m14-next118-composition-restart-20261028-1/cohort-successor-1'
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
source=load(PACKET/'check_source_contract.py','independent118_source_contract')
stream=io.StringIO()
with contextlib.redirect_stdout(stream):source.main()
(HERE/'SOURCE-CONTRACT.stdout').write_text(stream.getvalue())
m=load(PACKET/'test118_pipeline.py','independent118_existing_pipeline')
# Keep exact source paths/fixtures; redirect only the TemporaryDirectory parent
# into this reviewer's sole write allowlist. No producer output is overridden.
m.tempfile=types.SimpleNamespace(TemporaryDirectory=lambda prefix,dir:tempfile.TemporaryDirectory(prefix=prefix,dir=HERE))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(m.Pipeline))
(HERE/'PIPELINE.stdout').write_text(stream.getvalue())
report=dict(scope=__doc__.splitlines()[0],at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS_EXISTING_PURE_SOURCE_AND_REAL_CONSUMER_PIPELINE' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),pipeline_result=getattr(m.Pipeline,'result_record',None),CPU=0,jobs=1,AS_bytes=2*1024**3,actual_export=0,actual_materializer=0,actual_origin=0,actual_guard=0,actual_compiler=0,actual_Docker_native=0,temporary_fixture_pipeline=1)
(HERE/'PURE-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(stream.getvalue());print(json.dumps(report,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
