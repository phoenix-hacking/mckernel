"""Bind genuine new cycle stage through the accepted typed materializer only."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource
HERE=Path(__file__).resolve().parent
MATERIALIZER=Path('/home/holden/mckernel-work/host-preparation/current-ihk-native-logging-continuation-20261019-1/materialize_typed_runtime_cpu7.py')
PIN='2a9dc545e1da443e9956069572fb5946703b08a489a60cd826c2ff6ad7618ddb'
TARGET=Path('/home/holden/mckernel-work/scratch/hpf-host-261019-1')
PARENT=Path('/home/holden/mckernel-work/scratch/hpf-p-261019-1/a')
NONCE='03f9280c0b7896a86fd25a32dd9f63a8'
PINS={'owner.py.in': '20d93b032e4b6ed2380c77a42f1f70cad9ff47488d67f793d594ba4a7f325fec', 'runner.py.in': '9f019f861d5b4f43e1976b0e7c9fb3a4f7a8fe0837fd5e4c9203caaa3dab6ba1', 'typed_avx.py.in': 'c6b284d20ee7835a421ea628617be0e550b3c5ac221b2b69b6d65533856f3bab'}
def main():
 assert os.getuid()==1000 and os.sched_getaffinity(0)=={7}
 assert 0<resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824
 for name,pin in PINS.items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==pin
 raw=(HERE/'STAGE-BINDING-CONSUMED-SOURCES.json').read_bytes();b=json.loads(raw);stage=Path(b['output_root'])
 receipt=json.loads((stage/'stage-receipt.json').read_bytes())
 assert receipt['status']=='PASS_SOURCE_BOUND_FINAL_PUBLIC_RELEASE_INIT_ONLY_STAGE_ONLY' and receipt['binding_sha256']==hashlib.sha256(raw).hexdigest()
 assert receipt['module_changes']==[] and receipt['base_bytes_preserved'] is True and receipt['changed_roles']==['init']
 assert receipt['second_stop_protocol_prepared'] is True and receipt['final_public_release_protocol_prepared'] is True
 assert hashlib.sha256(MATERIALIZER.read_bytes()).hexdigest()==PIN
 spec=importlib.util.spec_from_file_location('accepted_cycle_typed_materializer',MATERIALIZER);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
 assert not TARGET.exists() and not PARENT.parent.exists()
 PARENT.parent.mkdir(mode=0o700);PARENT.mkdir(mode=0o700)
 with (HERE/'native-preparation-result.json').open('x') as stream:json.dump(dict(parent_identity=e.identity(PARENT.lstat(),PARENT),nonce=NONCE),stream,indent=2);stream.write('\n')
 e.N=HERE;e.TARGET=TARGET;e.MANIFEST=stage/'native-manifest.json';e.MANIFEST_SHA=hashlib.sha256(e.MANIFEST.read_bytes()).hexdigest()
 e.PINS=PINS
 e.main()
if __name__=='__main__':main()
