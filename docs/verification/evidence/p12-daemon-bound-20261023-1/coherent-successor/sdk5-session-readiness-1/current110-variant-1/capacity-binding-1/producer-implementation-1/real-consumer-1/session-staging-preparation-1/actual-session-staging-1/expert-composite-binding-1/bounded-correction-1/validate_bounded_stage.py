"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent
M=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/actual-session-staging-1/bounded-correction-1/actual-stage-1/manifest.json')
raw=M.read_bytes();assert hashlib.sha256(raw).hexdigest()=='6c3c80bff36af0f96ce05f73294c37f035a3e12d7fdc3aeeef88fc7532c11471'
spec=importlib.util.spec_from_file_location('bounded_current110_native_diagnostic',D/'source/native_diagnostic.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
accepted=native.load_manifest(str(M))
original=json.loads(raw);ref=original['staging']['overlay_manifest']
overlay=json.loads(Path(ref['path']).read_text())
negatives=[]
for label in ('launcher-bytes','launcher-mode','unexpected-member'):
 mutant=copy.deepcopy(original);changed=copy.deepcopy(overlay)
 if label=='launcher-bytes':changed['final_map']['bin/mcexec']['sha256']='0'*64
 elif label=='launcher-mode':changed['final_map']['bin/mcexec']['mode']=0o100700
 else:changed['final_map']['bin/unexpected']=copy.deepcopy(changed['final_map']['bin/mcexec'])
 output=D/(label+'.overlay.json');data=(json.dumps(changed,sort_keys=True)+'\n').encode()
 fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,ref['mode']&0o777)
 with os.fdopen(fd,'wb') as stream:stream.write(data)
 os.chmod(output,ref['mode']&0o777)
 mutant['staging']['overlay_manifest']={'path':str(output),'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':output.stat().st_mode}
 try:native._validate_manifest(mutant)
 except (ValueError,RuntimeError) as error:negatives.append({'label':label,'error':str(error)})
 else:raise AssertionError('accepted '+label)
assert raw==M.read_bytes(),'original manifest changed'
print(json.dumps({'status':'PASS_FULL_ACTUAL_CURRENT110_LOAD_MANIFEST_AND_BOUND_NEGATIVES','manifest_sha256':hashlib.sha256(raw).hexdigest(),'case_id':accepted['case_id'],'negative_controls':negatives,'native_acceptance':False,'archive_rebuilt':False}))
