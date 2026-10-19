"""Fresh8b case binding; unchanged accepted algorithm loaded by exact pin."""
from pathlib import Path
import hashlib,types
_LOADER={'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/fixed_case_loader.py', 'sha256': '6cb0986b5fbbb16e31eb1cdc593cbe3bea63d21b3093302da80eb966c22fc031', 'bytes': 1417}
_raw=Path(_LOADER['path']).read_bytes();assert len(_raw)==_LOADER['bytes'] and hashlib.sha256(_raw).hexdigest()==_LOADER['sha256']
_module=types.ModuleType('_fixed_fresh8b_loader');_module.__file__=_LOADER['path'];exec(compile(_raw,_module.__file__,'exec'),_module.__dict__)
_module.apply(globals(),'retain_finite_roles.py')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
 need(Path(args.release)==P/'retention-execution-release.json' and sha(Path(args.release))==args.release_sha256,'exact released input required')
 run(validate(json.loads(Path(args.release).read_bytes())))
