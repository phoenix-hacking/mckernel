"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root exact one-compose dispatcher invocation after genuine fresh grant, no retry.
"""
from pathlib import Path
import hashlib,json,os
D=Path(__file__).resolve().parent
profile=D/'PROFILE.NOT-GRANTED.json';grant=D/'ROOT-ACTUAL-ONE-COMPOSE-GRANT.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
argv=['/usr/bin/python3','-B',str(D/'run_one_compose.py'),'--profile',str(profile),'--profile-sha256',sha(profile),'--grant',str(grant),'--grant-sha256',sha(grant)]
with (D/'ROOT-ACTUAL-DISPATCH-LITERAL-ARGV.json').open('x') as f:json.dump(dict(scope=__doc__.splitlines()[0],argv=argv),f,indent=2);f.write('\n')
os.execv(argv[0],argv)
