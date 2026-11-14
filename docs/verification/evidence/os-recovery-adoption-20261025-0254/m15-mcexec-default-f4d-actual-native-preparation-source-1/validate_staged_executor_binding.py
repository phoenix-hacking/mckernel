"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only supplement to the existing complete native manifest/overlay validator.
Never stages or executes an image, loader, application, account guard or native owner.
"""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
CONTRACT=HERE/'SOURCE-BOUND-NATIVE-CONTRACT.json'
CONTRACT_SHA='0e3a0cf6e63914e9cc23b6e8a6850156f1cd2ad4a481b517e1354e76a1fed443'
def need(ok,why):
    if not ok:raise ValueError(why)
def read(ref):
    raw=Path(ref['path']).read_bytes();need(hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact reference');return json.loads(raw)
def check(manifest,overlay,c):
    binary=manifest['artifacts']['mcexec'];expected=c['installed']
    need(binary['path']==expected['path'] and binary['sha256']==expected['sha256'] and binary['size']==expected['bytes'] and binary['mode']==expected['mode'],'exact actual installed Rust executor selected')
    need(overlay['mcexec_sha256']==expected['sha256'] and overlay['sources']['mcexec']['path']==expected['path'] and overlay['sources']['mcexec']['sha256']==expected['sha256'],'actual overlay source selection')
    final=overlay['final_map'];row=final['bin/mcexec'];need(row['sha256']==expected['sha256'] and row['size']==expected['bytes'] and row['mode']==expected['mode'],'actual /bin/mcexec bytes')
    for name,p in c['providers'].items():
        row=final['lib64/'+name];need(row['sha256']==p['sha256'] and row['size']==p['bytes'] and row['mode']==p['mode'],'exact guest provider '+name)
        if name!='libnuma.so.1':
            key='loader' if name.startswith('ld-linux') else 'libc';need(manifest['artifacts'][key]['sha256']==p['sha256'],'manifest provider '+name)
        override=final.get('usr/local/lib64/'+name)
        need(override is None or override['sha256']==p['sha256'],'installed RPATH selects different provider '+name)
    need('etc/ld.so.cache' not in final,'preserve retained minimal base no-cache loader context')
    case=c['cases'].get(manifest['case_id']);need(case is not None,'retained exact case contract')
    need(manifest['payload']['argv']==case['argv'] and manifest['payload']['cwd']==case['cwd'] and manifest['payload']['env']==case['environment'],'unchanged case launch contract')
    for k,v in case['oracle'].items():need(manifest['payload']['oracle'][k]==v,'unchanged original case oracle '+k)
    need(manifest['artifacts']['payload']['sha256']==case['payload']['sha256'],'unchanged qualified application payload')
    need(manifest['profile']==c['profile'] or {k:manifest['profile'][k] for k in c['profile']}==c['profile'],'unchanged native resource profile')
    need({Path(r['path']).name:r['sha256'] for r in manifest['modules']}==c['required_unchanged_module_hashes'],'explicit unchanged module cohort')
    return dict(status='PASS_EXPLICIT_STAGED_RUST_EXECUTOR_BINDING_ONLY',case_id=manifest['case_id'],executor_sha256=expected['sha256'],mckernel_image=manifest['artifacts']['mckernel_image'],modules=manifest['modules'],native_executed=False,wholefile_acceptance=False,execution_authority=False)
def main():
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('manifest','manifest-sha256','loader-acceptance','loader-acceptance-sha256','output'):a.add_argument('--'+n,required=True)
    args=a.parse_args();need(hashlib.sha256(CONTRACT.read_bytes()).hexdigest()==CONTRACT_SHA,'frozen source contract')
    c=json.loads(CONTRACT.read_bytes());m=read(dict(path=args.manifest,sha256=args.manifest_sha256));overlay=read(m['staging']['overlay_manifest']);la=read(dict(path=args.loader_acceptance,sha256=args.loader_acceptance_sha256))
    need(la['status']=='ACTUAL_LOADER_COMPATIBILITY_PASS' and la['implementation_ownership'] is False and la.get('reviewer') and (la.get('actual_executor_sha256')==c['installed']['sha256'] or la.get('actual_installed_ELF',{}).get('sha256')==c['installed']['sha256']),'independent matching installedELF loader compatibility')
    result=check(m,overlay,c);result['loader_acceptance']=dict(path=args.loader_acceptance,sha256=args.loader_acceptance_sha256);result['manifest']=dict(path=args.manifest,sha256=args.manifest_sha256)
    with Path(args.output).open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
