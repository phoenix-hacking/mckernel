"""One original-refusal/corrected-positive actual consumed-path body check; no normalization or child."""
from pathlib import Path
import importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent
OLD=D.parent/'root-projection-bound-normalization-1'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def forbidden(*a,**k):raise AssertionError('no process/socket/root operation')
def main():
 subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
 normalizer=load('qualified_actual_consumed_paths_body',D/'prepare_batch_native.py')
 old=json.loads((OLD/'SETTINGS.json').read_bytes());new=json.loads((D/'SETTINGS.json').read_bytes())
 manifest=json.loads(Path(new['source_manifest']['path']).read_bytes())
 oldowner=load('original_actual_owner',old['runtime_owner']['path']);owner=load('corrected_actual_owner',new['runtime_owner']['path'])
 missing=manifest['artifacts']['mcexec']['path']
 try:normalizer.runtime_consumed_paths(Path(old['manifest_directory'])/'manifest.json',manifest,oldowner)
 except AssertionError as e:assert str(e)==missing
 else:raise AssertionError('original missing exact launcher root must refuse')
 consumed,roots=normalizer.runtime_consumed_paths(Path(new['manifest_directory'])/'manifest.json',manifest,owner)
 assert len(consumed)==79 and missing in consumed and roots.count(missing)==1
 assert [p for p in owner.EXTRA_READONLY if p not in [x.replace(str(Path(old['runtime_source_directory'])),str(Path(new['runtime_source_directory']))) for x in oldowner.EXTRA_READONLY]]==[missing]
 print(json.dumps(dict(status='PASS_ACTUAL_CONSUMED_PATHS_ORIGINAL_REFUSAL_AND_CORRECTED_POSITIVE_ONLY',consumed_paths=len(consumed),readonly_roots=len(roots),added_exact_file=missing,normalization_runs=0,guest_runs=0)))
if __name__=='__main__':main()
