"""Functional OS only; no security testing. Decode existing completed root export; no probe/cleanup."""
from pathlib import Path
import base64,hashlib,json,stat
E=Path(__file__).resolve().parent;SRC=E/'actual-retirement-export-1/stdout';D=E/'decoded-owner-export-1';D.mkdir(mode=0o700,exist_ok=False)
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
x=json.loads(SRC.read_text());assert ref(SRC)['sha256'].startswith('57bc9a87')and x['status']=='READONLY_EXACT_CLOSED_OWNER_EVIDENCE_EXPORT'and x['root_mutations']==0 and x['root_identity']['uid']==x['root_identity']['gid']==0 and x['root_identity']['mode']==0o700
rows=[];total=0
for r in x['files']:
 name=r['name'];assert name not in ['.','..']and'/'not in name;raw=base64.b64decode(r['base64'],validate=True);meta=r['identity'];assert len(raw)==meta['st_size']and hashlib.sha256(raw).hexdigest()==r['sha256']and stat.S_ISREG(meta['st_mode'])and meta['st_nlink']==1
 p=D/name
 with p.open('xb')as f:f.write(raw)
 p.chmod(0o600);rows.append(dict(name=name,source_path=r['source_path'],source_identity=meta,source_sha256=r['sha256'],retained=ref(p)));total+=len(raw)
assert total==x['total_source_bytes'];result=dict(scope=__doc__.splitlines()[0],status='PASS_ACTUAL_ROOT_OWNER_EXPORT_DECODED_BYTE_EXACT',source_export=ref(SRC),root=x['root'],root_identity=x['root_identity'],files=rows,total_source_bytes=total,root_or_Docker_or_cleanup_effects=0)
(E/'ACTUAL-OWNER-EXPORT-RETENTION-MAP.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status=result['status'],files=len(rows),total=total,names=[r['name']for r in rows if r['name'].endswith('.json')]),indent=2))
