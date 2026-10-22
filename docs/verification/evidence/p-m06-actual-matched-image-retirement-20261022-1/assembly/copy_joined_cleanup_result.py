"""Exact joined stdout copy only. Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os
A=Path(__file__).resolve().parent;E=A.parent;B=E/'bound-matched-image-terminal-source-2'
def sha(v):return hashlib.sha256(v).hexdigest()
release=json.loads((E/'ROOT-CLEANUP-EXECUTION-RELEASE-2.json').read_bytes());capture=A/'actual-cleanup-capture-1';status=json.loads((capture/'status.json').read_bytes())
assert status['returncode']==0 and status['direct_child_joined']is True and status['process_group_absent']is True and status['streams_closed']is True
assert not(capture/'stderr').read_bytes();raw=(capture/'stdout').read_bytes();assert len(raw)==status['stdout']['bytes'] and sha(raw)==status['stdout']['sha256'];result=json.loads(raw)
spec=importlib.util.spec_from_file_location('copy_exact_engine',B/'cleanup_pass_image.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert result['status']=='PASS_EXECUTED'and result['terminal']is True and result['container_absent']is True and result['container_id']==release['observation']['target']['container_id']and result['release_sha256']==m.digest(m.canonical(release))
p=A/'actual-cleanup-result.json'
with p.open('xb')as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(status='PASS_EXACT_JOINED_CLEANUP_STDOUT_COPY',path=str(p),sha256=sha(raw),bytes=len(raw),cleanup_reexecuted=False),sort_keys=True))
