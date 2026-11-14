"""Exercise actual final _runtime/_bind_m07; no normalization/backend/guest."""
from pathlib import Path
import hashlib,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def forbidden(*a,**k):raise AssertionError('no process/socket/backend effect in sourcegraph boundary')
def main():
 cfg=json.loads((D/'SETTINGS.json').read_bytes());R=Path(cfg['runtime_source_directory']);future=Path(cfg['manifest_directory'])/'manifest.json'
 assert not future.exists() and not Path(cfg['attempt_parent']).parent.exists()
 subprocess.Popen=forbidden;subprocess.run=forbidden;socket.socket=forbidden;os.execve=forbidden
 runner=load('actual_final_source4_runner',R/'native_diagnostic_runner.py')
 diagnostic,backend=runner._runtime()
 assert runner._HERE==R and Path(diagnostic.__file__).resolve()==R/'native_diagnostic.py'
 staged=diagnostic.load_manifest(cfg['source_manifest']['path'])
 try:runner._bind_m07(diagnostic,staged,future)
 except diagnostic.DiagnosticError as error:
  assert isinstance(error.__cause__,FileNotFoundError),repr(error)
  assert error.__cause__.filename==str(future),error.__cause__.filename
  missing=str(error)
 else:raise AssertionError('future final manifest unexpectedly readable')
 owner=load('actual_final_source4_owner',R/'native_diagnostic_container_owner.py')
 selected={r['path']:r['sha256'] for r in cfg['runtime_source_pins']}
 assert selected==dict(owner.SOURCE_HASHES,**{owner.SELF:cfg['runtime_owner']['sha256']})
 assert owner.RUNNER==str(R/'native_diagnostic_runner.py')
 for path,expected in selected.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
 assert not future.exists() and not Path(cfg['attempt_parent']).parent.exists()
 print(json.dumps(dict(status='PASS_ACTUAL_SOURCE4_IDENTITY_GATES_TO_EXACT_MISSING_FUTURE_MANIFEST_ONLY',actual_runtime=True,actual_bind_m07=True,actual_fresh_HERE=True,source_identities_passed=True,source_count=len(selected),expected_missing_manifest=str(future),actual_refusal=missing,complete_manifest_binding=False,normalization=False,metadata_created=False,backend_entered=False,guest_runs=0,root_operations=0),sort_keys=True))
if __name__=='__main__':main()
