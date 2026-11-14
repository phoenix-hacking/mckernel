"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind an ALREADY Root-composed original-case overlay using existing full validators.
No composition, compiler, guest, resource observation, ledger or account operation.
"""
import argparse,copy,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN=HERE/'ORIGINAL-CASES-SUCCESSOR.NOT-RELEASED.json'
PLAN_SHA='8a232e500f5b496106f148a7d934d3bd71c08429d0dcbf7e258873d99413441a'
def need(ok,why):
    if not ok:raise ValueError(why)
def ref(p):
    p=Path(p);raw=p.read_bytes();s=p.stat();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=s.st_mode)
def bound(r):
    actual=ref(r['path']);need(all(actual[k]==v for k,v in r.items()),'frozen reference changed');return json.loads(Path(r['path']).read_bytes())
def module(name,r):
    need(ref(r['path'])==r,'existing source byte binding');spec=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--case',choices=['startup','strict235'],required=True)
    for n in ['overlay-receipt','overlay-receipt-sha256','output']:a.add_argument('--'+n,required=True)
    args=a.parse_args();need(ref(PLAN)['sha256']==PLAN_SHA,'exact source plan');p=json.loads(PLAN.read_bytes());case=p['cases'][args.case];receipt=bound(dict(path=str(Path(args.overlay_receipt).resolve()),sha256=args.overlay_receipt_sha256));output=Path(case['expected_output']);m=copy.deepcopy(case['manifest_proposal'])
    need(receipt['base_sha256']==p['source_base']['sha256'] and receipt['base_cpio_sha256']==p['source_base_raw']['base_cpio_sha256'] and receipt['base_cpio_size']==p['source_base_raw']['base_cpio_size'],'unchanged chosen base')
    for key,r in [('base',p['source_base']),('payload',m['artifacts']['payload']),('collector',p['collector']),('mcexec',p['selected_executor'])]:need(receipt['sources'][key]['path']==r['path'] and receipt['sources'][key]['sha256']==r['sha256'],'exact actual overlay '+key)
    actual=ref(output);need(actual['sha256']==receipt['output_sha256'] and actual['size']==receipt['size'],'actual composed output')
    m['staging']['derived_initramfs']=actual;m['staging']['overlay_manifest']=ref(Path(args.overlay_receipt).resolve())
    loader=bound(p['installed_loader_acceptance']);need(loader['status']=='ACTUAL_LOADER_COMPATIBILITY_PASS' and loader['actual_executor_sha256']==p['selected_executor']['sha256'] and loader['implementation_ownership'] is False,'actual matching installed loader acceptance')
    diagnostic=module('exact_bound_native_original_case_validator',p['diagnostic']);validated=diagnostic._validate_manifest(m)
    supplement_path=HERE.parent/'validate_staged_executor_binding.py';spec=importlib.util.spec_from_file_location('retained_executor_binding_supplement',supplement_path);supplement=importlib.util.module_from_spec(spec);spec.loader.exec_module(supplement);contract=json.loads(supplement.CONTRACT.read_bytes());need(hashlib.sha256(supplement.CONTRACT.read_bytes()).hexdigest()==supplement.CONTRACT_SHA,'frozen existing executor supplement');supplement.check(m,receipt,contract)
    need(validated['payload']==m['payload'],'original payload/oracle unchanged by validation')
    with Path(args.output).open('x') as f:json.dump(m,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(status='BOUND_ORIGINAL_CASE_RUST_EXECUTOR_MANIFEST_NOT_RUNTIME_RELEASE',case_id=m['case_id'],manifest=ref(args.output),selected_executor=p['selected_executor'],image=m['artifacts']['mckernel_image'],execution_authority=False)))
if __name__=='__main__':main()
