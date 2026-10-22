"""Bounded actual runner binding regression; no backend, attempt, guest or root."""
from pathlib import Path
import hashlib,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent

def checked(row):
 raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 return raw

def load(name,row):
 checked(row)
 spec=importlib.util.spec_from_file_location(name,row['path'])
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
 return result

def forbidden(*args,**kwargs):raise AssertionError('no backend/process/socket/guest in runner body check')

def main():
 assert os.getuid()==os.geteuid()==1000
 cfg=json.loads((D/'RUNNER-ACTUAL-BODY-CHECK-INPUTS.json').read_bytes())
 for key in ('original','candidate','diagnostic','adapter','parser','manifest','owner'):checked(cfg[key])
 subprocess.Popen=forbidden;subprocess.run=forbidden;socket.socket=forbidden;os.execve=forbidden
 original=load('_original_missing_import_runner',cfg['original'])
 diagnostic=original._module('_real_original_diagnostic',cfg['original_diagnostic']['path'])
 manifest=diagnostic.load_manifest(cfg['manifest']['path'])
 try:original._bind_m07(diagnostic,manifest,Path(cfg['manifest']['path']))
 except NameError as error:
  assert str(error)=="name 'hashlib' is not defined";negative=str(error)
 else:raise AssertionError('original missing import not reproduced')
 candidate=load('_corrected_real_runner',cfg['candidate'])
 # The actual candidate now has real fresh siblings. No _HERE override or
 # function replacement is used, and no historical stdout is expected.
 assert candidate._HERE==Path(cfg['runtime_source_directory'])
 diagnostic=candidate._module('_real_current_diagnostic',cfg['diagnostic']['path'])
 manifest=diagnostic.load_manifest(cfg['manifest']['path'])
 candidate._bind_m07(diagnostic,manifest,Path(cfg['manifest']['path']))
 assert diagnostic.evaluate.__module__=='m07_runner_case'
 adapter=candidate._module('_real_current_typed_case',cfg['adapter']['path'])
 bound,parser,frozen=adapter.binding(cfg['manifest']['path'],cfg['manifest']['sha256'])
 assert bound._same_plan(bound._freeze(bound._thaw(manifest)),bound._freeze(bound._thaw(frozen)))
 owner=load('_real_fresh_typed_owner',cfg['owner'])
 owner_diagnostic,owner_manifest=owner.bound_manifest(cfg['manifest']['path'],cfg['manifest']['sha256'])
 assert owner_diagnostic._same_plan(owner_diagnostic._freeze(owner_diagnostic._thaw(owner_manifest)),owner_diagnostic._freeze(owner_diagnostic._thaw(frozen)))
 assert owner.RUNNER==cfg['candidate']['path'] and owner.SOURCE_HASHES[owner.RUNNER]==cfg['candidate']['sha256']
 assert parser.SUFFIX==adapter.SENTINEL and len(parser.SUFFIX)==120
 print(json.dumps(dict(status='PASS_ACTUAL_FRESH_RUNNER_OWNER_TYPED_MANIFEST_AND_PARSER_BINDING_ONLY',original_negative=negative,actual_runner_binding=True,typed_adapter_installed=True,actual_normalized_manifest_sha256=cfg['manifest']['sha256'],parser_sha256=cfg['parser']['sha256'],reference_parser_fixture_only=False,actual_fresh_HERE=True,actual_owner_runner_hash_join=True,bound_parser=True,current_full_stdout_expected=None,backend_entered=False,attempt_created=False,child_processes=0,guest_runs=0,root_operations=0,current_native_acceptance=False),sort_keys=True))
if __name__=='__main__':main()
