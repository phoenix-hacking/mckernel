"""Pure minimum-caps binding only; no guard, controller, or process access."""
import hashlib, importlib.util, json
from pathlib import Path
HELPER = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/weekly_source_bindings.py', 'bytes': 3108, 'sha256': '7cf5be38eaa4a1a96a1451c6b87d174d8d545e78c0279001524184524c07b1a4'}
AUTH = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/USER-WEEKLY-ONLY-AUTHORIZATION.json', 'bytes': 1391, 'sha256': '234367690e532f77670374986be31fbe2ce66e9bdf3dd302da9af38f62a93c68'}
WINDOW = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/ACTUAL-WINDOW.json', 'bytes': 1373, 'sha256': 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'}

def read(row):
    p=Path(row['path']); b=p.read_bytes()
    if p.is_symlink() or len(b)!=row['bytes'] or hashlib.sha256(b).hexdigest()!=row['sha256']: raise ValueError('exact source bytes')
    return json.loads(b)

def weekly_limits(armed, bootstrap):
    p=Path(HELPER['path']); b=p.read_bytes()
    if p.is_symlink() or len(b)!=HELPER['bytes'] or hashlib.sha256(b).hexdigest()!=HELPER['sha256']: raise ValueError('exact helper bytes')
    spec=importlib.util.spec_from_file_location('retained_weekly_minimum_caps', p)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    return helper.minimum_caps(read(AUTH),read(WINDOW),bootstrap,armed['caps'])
