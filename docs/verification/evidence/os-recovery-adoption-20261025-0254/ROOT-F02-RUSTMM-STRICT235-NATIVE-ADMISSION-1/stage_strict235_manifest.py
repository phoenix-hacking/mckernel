"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-selected ordinary manifest stage before the admission clock; never a guest.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
A=Path(__file__).resolve().parent

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage-root',required=True);args=parser.parse_args()
 assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
 b=json.loads((A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes());source=Path(b['offline_manifest']['path']);assert ref(source)==b['offline_manifest'];raw=source.read_bytes();digest=b['offline_manifest']['sha256']
 stage=Path(args.stage_root);scratch=Path('/home/holden/mckernel-work/scratch');assert str(stage)==args.stage_root and stage.is_absolute() and '..' not in stage.parts and stage.parent==scratch and stage.parent.resolve(strict=True)==scratch and not os.path.lexists(stage)
 parent=stage/'p';target=stage/'m.json'
 owner=Path(b['owner_source']['path']);assert ref(owner)==b['owner_source']
 spec=importlib.util.spec_from_file_location('retained_strict235_pure_owner',owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 validator=owner.with_name('native_diagnostic.py');assert hashlib.sha256(validator.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c'
 spec=importlib.util.spec_from_file_location('retained_strict235_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 manifest=v.load_manifest(source)
 # A zero-filled string is only a pure pathname-length vector, not an actual nonce.
 v.expected_qemu_argv(manifest,parent/('attempt-'+'0'*32))
 stage.mkdir(mode=0o700);parent.mkdir(mode=0o700)
 with target.open('xb') as stream:stream.write(raw)
 assert target.read_bytes()==raw and not list(parent.iterdir())
 m._manifest_identity(str(target),digest);m._manifest_outside_writable_parent(str(target),str(parent));v.load_manifest(target)
 receipt=dict(scope=__doc__.splitlines()[0],status='PASS_EXCLUSIVE_ORDINARY_SCRATCH_STAGE_AND_TWO_OWNER_PURE_PATH_GUARDS',source_manifest=b['offline_manifest'],scratch_manifest=ref(target),planned_attempt_parent=str(parent),parent_uid=parent.stat().st_uid,parent_gid=parent.stat().st_gid,parent_mode=oct(parent.stat().st_mode),parent_empty=True,checks=['_manifest_identity','_manifest_outside_writable_parent','existing_native_load_manifest','pure_expected_qemu_argv_path_length'],kernel_image_unchanged=True,overlay_unchanged=True,runtime_authority=None,nonce=None,resources=None,review=None)
 with (A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json').open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
 print(json.dumps(receipt))
if __name__=='__main__':main()
