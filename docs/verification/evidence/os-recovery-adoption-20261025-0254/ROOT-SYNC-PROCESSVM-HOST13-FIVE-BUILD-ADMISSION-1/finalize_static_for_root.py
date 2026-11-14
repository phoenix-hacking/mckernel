"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-invoked finite metadata finalization AFTER FP join/canonical adoption.
No workload, clock, resource capture, Git action or execution grant is performed.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');Q=E/'qualified-sync-processvm-host13-five-stage-source-1'
def read(p):return json.loads(p.read_text())
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def encode(x):return (json.dumps(x,indent=2)+'\n').encode()
def new(p,x):
 with p.open('xb') as stream:stream.write(encode(x))
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--clearance',type=Path,required=True);parser.add_argument('--source-adoption',type=Path,required=True);parser.add_argument('--source-review',type=Path,required=True);parser.add_argument('--nonce',required=True);args=parser.parse_args()
 assert os.getuid()==os.geteuid()==1000 and re.fullmatch('[0-9a-f]{32}',args.nonce)
 # These actual paths are supplied by Root after the actual FP normal join.
 # No historical physical receipt is selected by this helper.
 for p in [args.clearance,args.source_adoption,args.source_review]:assert p.is_absolute() and p.resolve(strict=True)==p;read(p)
 plan=read(Q/'COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json')
 for relative,row in plan['postimages'].items():
  p=R/relative;actual=ref(p);assert (actual['bytes'],actual['sha256'])==(row['bytes'],row['sha256']),('canonical postimage not adopted',relative)
 mirror=read(D/'CANONICAL-RUST-MIRROR.TEMPLATE.NOT-ATTESTED.json')
 for row in mirror['rows']:assert ref(Path(row['expected_canonical']['path']))==row['expected_canonical']
 names=['STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json','PROFILE.SOURCE-ONLY.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json','ROOT-REQUEST-ADOPTION.json','ROOT-HOLDER-BOOTSTRAP-GRANT.json','CANONICAL-RUST-MIRROR-BINDING.SOURCE-ONLY.json']
 assert all(not os.path.lexists(D/name) for name in names)
 assert not (D/'HOLDER').exists() and not (D/'OUTPUT').exists()
 request=read(D/'STATIC-REQUEST-PAYLOAD.TEMPLATE.NOT-AUTHORITY.json');request.update(status='ROOT_BOUND_COMBINED_FIVE_STATIC_REQUEST_NO_EXECUTION_AUTHORITY',nonce=args.nonce,source_adoption=ref(args.source_adoption),independent_source_profile_review=ref(args.source_review),current_physical_clearance=ref(args.clearance),actual_handshake_root=str(D/'HOLDER'),actual_output_root=str(D/'OUTPUT'))
 request_bytes=encode(request);request_sha=hashlib.sha256(request_bytes).hexdigest()
 profile=read(D/'PROFILE.TEMPLATE.NOT-RELEASED.json');profile.update(request_sha256=request_sha,native_custody_clearance=ref(args.clearance))
 export=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');export.update(author='/root',decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',request_sha256=request_sha,runtime_authority=None)
 # Verify exact inherited source-export API and all selected readable bytes
 # before writing any actual metadata; this calls no execution/capture method.
 spec=importlib.util.spec_from_file_location('existing_fixed_five_static_finalization',D/'run_build_only.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 assert len(runner.commands_for_plan(profile))==5
 refs=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in profile['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(profile)]
 assert refs==export['qualified_readonly_files']
 for row in refs:runner.auth(row)
 assert sum(not r['replace'] for r in profile['inputs']['objects'])==7
 bootstrap=read(D/'ROOT-HOLDER-BOOTSTRAP.TEMPLATE.NOT-GRANTED.json');bootstrap.update(author='/root',decision='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER',nonce=args.nonce,fresh_handshake_root=str(D/'HOLDER'),native_custody_clearance=ref(args.clearance))
 new(D/names[0],request);new(D/names[1],profile);new(D/names[2],export)
 adoption=dict(author='/root',decision='ADOPT_EXACT_COMBINED_FIVE_STATIC_SOURCE_REQUEST_NOT_EXECUTION',runtime_authority=None,nonce=args.nonce,request=ref(D/names[0]),request_sha256=request_sha,source_adoption=ref(args.source_adoption),independent_source_profile_review=ref(args.source_review),current_physical_clearance=ref(args.clearance),profile=ref(D/names[1]),input_export=ref(D/names[2]),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None);new(D/names[3],adoption)
 bootstrap['profile']=ref(D/names[1]);new(D/names[4],bootstrap)
 mirror.update(status='ROOT_OBSERVED_EXACT_POSTADOPTION_CANONICAL_106_FILE_MIRROR_NOT_FETCH_VERIFICATION',source_adoption=ref(args.source_adoption),actual_postadoption_match=True)
 for row in mirror['rows']:row['actual_postadoption_match']=True;row['current_canonical']=ref(Path(row['expected_canonical']['path']))
 new(D/names[5],mirror)
 print(json.dumps(dict(status='ROOT_STATIC_FIELDS_BOUND_FOR_SINGLE_PUBLICATION_BEFORE_CLOCK',request_sha256=request_sha,profile=ref(D/names[1]),source_adoption=ref(args.source_adoption),current_physical_clearance=ref(args.clearance),actual_execution_release=False)))
if __name__=='__main__':main()
