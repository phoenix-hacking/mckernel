"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run the existing pure recursive fixture once in this review-only namespace.
No actual guard/account/observation/native/compiler/nonce/producer calls.
"""
from pathlib import Path
import contextlib,datetime,hashlib,importlib.util,io,json,resource,sys,traceback
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
HERE=Path(__file__).resolve().parent
PACKET=HERE.parent.parent/'original227-runtime-bindings-restart-20261028-1/recursive-successor-1'
sys.path.insert(0,str(PACKET))
spec=importlib.util.spec_from_file_location('independent_original227_recursive_fixture',PACKET/'test_recursive_successor.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.D=HERE/'SYNTHETIC-REVIEW-FIXTURE-1'
out=io.StringIO();err=io.StringIO();ok=False
try:
 with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):module.main()
 ok=True
except BaseException:
 traceback.print_exc(file=err)
finally:
 (HERE/'PURE-REGRESSION.stdout').write_text(out.getvalue())
 (HERE/'PURE-REGRESSION.stderr').write_text(err.getvalue())
 status=dict(scope=__doc__.splitlines()[0],at=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision='PASS_EXISTING_SIX_PURE_RECURSIVE_GROUPS' if ok else 'FAIL_PURE_RECURSIVE_FIXTURE',fixture_source_sha256=hashlib.sha256((PACKET/'test_recursive_successor.py').read_bytes()).hexdigest(),fixture_namespace=str(module.D),CPU=0,jobs=1,AS_bytes=2*1024**3,actual_guard_calls=0,actual_account_calls=0,actual_observations=0,actual_command_replies=0,synthetic_command_replies=26,nonce_calls=0,native_calls=0)
 (HERE/'PURE-REVIEW-RESULT.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status,indent=2))
if not ok:print(err.getvalue());raise SystemExit(1)
