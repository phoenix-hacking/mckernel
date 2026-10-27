"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-review proposal: exact canonical source adoption or binding existing actual
materialization. No compiler, subprocess, clock/admission, container or native run.
Default checks only. Root alone may invoke the two explicit mutation modes.
"""
import argparse, hashlib, json, os, re, stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
MANIFEST=HERE/'SOURCE-ADOPTION-MANIFEST.json'
MANIFEST_SHA='277ee83ef81aade4cba07840a3456252b67c200ae1bd4616fde03c1f3910d112'
def need(ok,why):
    if not ok: raise ValueError(why)
def load(path): return json.loads(Path(path).read_bytes())
def safe(path):
    p=Path(path);need(p.is_absolute() and '..' not in p.parts,'absolute path required')
    need(all(not q.is_symlink() for q in (p,*p.parents)),'symlink path refused')
    return p
def ref(p):
    p=safe(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def matches(p,r):
    actual=ref(p);return all(actual[k]==r[k] for k in ('bytes','sha256'))
def node(p):
    p=safe(p);s=p.stat();need(stat.S_ISDIR(s.st_mode),'directory required')
    return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def newjson(p,value):
    with safe(p).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def check_sources(m,post=False):
    for r in m['rows']:
        t=safe(r['target']);need(matches(r['postimage']['path'],r['postimage']),'provider changed '+r['relative'])
        expected=r['postimage'] if post else r['preimage']
        need((not os.path.lexists(t)) if expected is None else matches(t,expected),'canonical changed '+r['relative'])
def main():
    a=argparse.ArgumentParser(description=__doc__);g=a.add_mutually_exclusive_group()
    g.add_argument('--apply-canonical',action='store_true');g.add_argument('--bind-runtime',action='store_true')
    a.add_argument('--materialization');a.add_argument('--receipt');args=a.parse_args()
    need(hashlib.sha256(MANIFEST.read_bytes()).hexdigest()==MANIFEST_SHA,'manifest preimage changed')
    m=load(MANIFEST);co=Path(m['cohort']);p=load(co/'PREPARATION.json')
    need(matches(co/'PREPARATION.json',m['preparation_preimage']),'preparation preimage changed')
    if args.bind_runtime:
        need(args.materialization and args.receipt,'actual materialization and fresh receipt required')
        check_sources(m,post=True);mr=ref(args.materialization);mat=load(args.materialization)
        need(mat['status']=='PASS_FINITE_TARGET_SOURCE_MATERIALIZATION_ONLY','actual materialization status')
        src=safe(mat['source_root']);need(node(src)==mat['source_identity'],'materialization node identity')
        expected={r['relative']:r['postimage'] for r in m['rows']}
        expected.update({'executer/user/rust/'+name:r for name,r in m['qualification_only_inputs'].items()})
        for rel,r in expected.items():need(matches(src/rel,r),'materialized selected source '+rel)
        prefix=safe(p['runtime']['retained_prefix_root'])
        for r in p['retained_prefix_files']:need(matches(prefix/r['relative'],r),'retained prefix '+r['relative'])
        found=re.findall(r'^RUSTC:[^=]+=([^\n]+)$',(prefix/'CMakeCache.txt').read_text(),re.M)
        need(found==['/nightly/bin/rustc'],'actual preserved compute compiler')
        vendor=safe(p['libdwarf_vendor']['HOST_root']);vi=node(vendor)
        need(all(vi[k]==v for k,v in p['libdwarf_vendor']['HOST_identity'].items()),'vendor identity changed')
        r=p['runtime'];r.update(adopted=True,source_root=str(src),source_identity=node(src),materialization=mr,retained_prefix_identity=node(prefix),vendor_source=str(vendor),vendor_identity=vi,preserved_compute_RUSTC=found[0])
        # Save exact predecessor before replacing mutable Root adoption data.
        receipt=safe(args.receipt);need(not os.path.lexists(receipt),'fresh receipt required')
        newjson(receipt,dict(status='ROOT_RUNTIME_BINDING_INPUTS_CHECKED_NOT_EXECUTION_RELEASE',preparation_preimage=m['preparation_preimage'],runtime=r,execution_authority=False))
        # These actual_* fields remain NULL until Root authenticates current controls.
        temp=co/'PREPARATION.ROOT-BOUND.tmp';newjson(temp,p);os.replace(temp,co/'PREPARATION.json')
        print(json.dumps(dict(status='ROOT_RUNTIME_BINDINGS_WRITTEN_REQUIRE_ADOPTION_PREFLIGHT_AND_NEW19_MAP',preparation=ref(co/'PREPARATION.json'),execution_authority=False)));return
    check_sources(m)
    if args.apply_canonical:
        need(args.receipt and not os.path.lexists(args.receipt),'fresh receipt required')
        # All preimages and providers validated before first write. No rollback
        # overwrites other writers; interruption requires explicit reconciliation.
        for r in m['rows']:
            if not r['write_required']:continue
            t=safe(r['target']);t.parent.mkdir(parents=True,exist_ok=True)
            if r['preimage'] is None:
                with t.open('xb') as f:f.write(Path(r['postimage']['path']).read_bytes())
            else:
                need(matches(t,r['preimage']),'preimage changed during apply')
                with t.open('wb') as f:f.write(Path(r['postimage']['path']).read_bytes())
            need(matches(t,r['postimage']),'canonical postimage')
        check_sources(m,post=True)
        newjson(args.receipt,dict(status='ROOT_EXACT19_SOURCE_ADOPTION_ONLY',rows=m['rows'],execution_authority=False))
    print(json.dumps(dict(status='PASS_EXACT19_SOURCE_POSTIMAGES' if args.apply_canonical else 'PASS_EXACT19_PREIMAGES_AND_PROVIDERS',writes=m['canonical_write_files'] if args.apply_canonical else 0,execution_authority=False)))
if __name__=='__main__':main()
