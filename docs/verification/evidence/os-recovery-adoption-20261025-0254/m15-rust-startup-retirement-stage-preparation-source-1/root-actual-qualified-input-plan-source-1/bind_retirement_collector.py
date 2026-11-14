"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Check source, or bind ALREADY Root-composed bytes. No compose/runtime/guard/query.
"""
import argparse,copy,hashlib,importlib.util,json,os,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN=HERE/'STAGE-PLAN.NOT-RELEASED.json'
PLAN_SHA='d22d9f2988df091aade281cbb7b0534d59fc21d0c8a0999f64b2db0c1ede1ef9'
def need(ok,why):
 if not ok:raise ValueError(why)
def read(path):
 p=Path(path);need(p.is_absolute() and p.resolve(strict=True)==p,'literal input path')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());need(stat.S_ISREG(a.st_mode) and a.st_size<=32*2**20,'finite regular input')
  b=f.read(32*2**20+1);z=os.fstat(f.fileno())
  keys=('st_dev','st_ino','st_nlink','st_uid','st_gid','st_mode','st_size','st_mtime_ns','st_ctime_ns')
  need(len(b)==a.st_size and all(getattr(a,k)==getattr(z,k) for k in keys),'stable complete input')
 return b,a

def ref(path):
 b,a=read(path);return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),size=len(b),mode=a.st_mode)
def checked(r):
 b,a=read(r['path']);actual=dict(path=r['path'],sha256=hashlib.sha256(b).hexdigest(),size=len(b),bytes=len(b),mode=a.st_mode)
 need(all(actual[k]==v for k,v in r.items() if k in actual),'exact frozen input '+r['path']);return b

def data(r):return json.loads(checked(r))
def module(name,r):
 checked(r);spec=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 need(m.__file__==r['path'] and m.__spec__.origin==r['path'],'literal import context');return m

def check_collector(m,receipt,p,facts,profile):
 need(m['case_id']==facts['case_id']==profile['case_id']=='startup.argv-empty','compiled case id')
 need(m['payload']['argv']==facts['payload_argv']==profile['argv']==['/bin/mcexec','-t','1','0','app','A','','B'],'actual compiled collector argv')
 need(m['payload']['cwd']==facts['payload_cwd']==profile['cwd']=='/case/work','compiled cwd')
 need(m['payload']['env']==facts['payload_env']==profile['env']=={'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps'},'compiled twoenv')
 need(m['payload']['oracle']==facts['oracle']==profile['oracle'] and len(bytes.fromhex(facts['oracle']['stdout_hex']))==91,'unchanged91B oracle')
 need(type(p['qualified_actual_test_count']) is int and p['qualified_actual_test_count']>0 and facts['actual_test_count']==p['qualified_actual_test_count'] and facts['ignored']==facts['filtered']==0,'exact actual new qualification count; no ignored/filtered')
 need(facts['source_caseprofile']['sha256']==p['compiled_collector_profile']['sha256'],'qualified compiled profile join')
 expected=p['collector'];need(m['staging']['collector']==expected,'exact collector selection')
 need(facts['actual_collector_artifact']['path']==expected['path'] and facts['actual_collector_artifact']['sha256']==expected['sha256'] and facts['actual_collector_artifact']['bytes']==expected['size'],'actual artifact qualification')
 need(facts['startup_boot_argv']==profile['startup_boot_argv']==['/bin/native-boot'],'original boot argv')
 for name,v in [('stdout_limit_bytes',1024),('stderr_limit_bytes',1024)]:need(m['payload'][name]==facts['limits'][name]==profile[name]==v,'unchanged '+name)
 need(facts['limits']['payload_timeout_ms']==profile['payload_timeout_ms']==10000 and facts['limits']['post_reap_retirement_ms']==profile['post_reap_retirement_ms']==5000,'original deadlines')
 if receipt is not None:
  need(receipt['collector_sha256']==expected['sha256'] and receipt['sources']['collector']['path']==expected['path'] and receipt['sources']['collector']['sha256']==expected['sha256'],'actual collector producer selection')
  row=receipt['final_map']['init'];need(row['sha256']==expected['sha256'] and row['size']==expected['size'] and row['mode']==stat.S_IFREG|0o755,'actual /init compiled profile bytes')
 return True

def source_check():
 need(ref(PLAN)['sha256']==PLAN_SHA,'frozen finite plan');p=json.loads(PLAN.read_bytes())
 for r in p['references'].values():checked(r)
 for r in [p['collector'],p['selected_executor'],p['source_base'],p['payload'],p['image'],*p['modules']]:checked(r)
 facts=data(p['compiled_collector_binding_facts']);profile=data(p['compiled_collector_profile']);ad=data(p['references']['Root_collector_adoption'])
 need(ad['actual_artifact']['sha256']==p['collector']['sha256'] and ad['actual_binding_facts']['sha256']==p['compiled_collector_binding_facts']['sha256'],'Root adopted correct producer qualification')
 check_collector(p['manifest_template'],None,p,facts,profile)
 old=data(p['references']['failed_be6e_manifest']);expected=copy.deepcopy(old);expected['staging']['collector']=p['collector'];expected['staging']['derived_initramfs']=None;expected['staging']['overlay_manifest']=None
 need(expected==p['manifest_template'],'only collector and unbound derived receipt inputs differ')
 need(all(p[k] is None for k in ['current_free','current_ledger','nonce','source_authority','native_release','actual_compose_receipt','actual_manifest','actual_binding']),'future current/grant/actual outputs null')
 diagnostic=module('literal_correct_startup_diagnostic',p['references']['diagnostic']);diagnostic._validate_payload_argv(p['manifest_template']['payload']['argv']);diagnostic._validate_cleanup_profile(p['manifest_template']['cleanup_profile'],p['modules'])
 owner=module('literal_correct_startup_owner',p['references']['normal_owner']);need(callable(owner._manifest_identity) and callable(owner._manifest_outside_writable_parent),'original owner data API')
 return p,facts,profile,diagnostic,owner

def bind(p,facts,profile,diagnostic,owner,receipt_path,receipt_sha):
 need(str(Path(receipt_path))==p['expected_receipt'],'exact Root actual stdout receipt namespace');r=ref(Path(receipt_path));need(r['sha256']==receipt_sha,'actual Root receipt hash');receipt=json.loads(checked(r));m=copy.deepcopy(p['manifest_template'])
 need(receipt['base_sha256']==p['source_base']['sha256'] and receipt['base_cpio_sha256']==p['source_base_raw']['base_cpio_sha256'] and receipt['base_cpio_size']==p['source_base_raw']['base_cpio_size'],'same exact base/raw CPIO')
 for key,source in [('base',p['source_base']),('payload',p['payload']),('collector',p['collector']),('mcexec',p['selected_executor'])]:need(receipt['sources'][key]['path']==source['path'] and receipt['sources'][key]['sha256']==source['sha256'],'actual source '+key)
 output=ref(Path(p['expected_output']));need(output['sha256']==receipt['output_sha256'] and output['size']==receipt['size'],'actual Root composed output');m['staging']['derived_initramfs']=output;m['staging']['overlay_manifest']=r
 check_collector(m,receipt,p,facts,profile)
 validated=diagnostic._validate_manifest(m);need(validated['payload']==m['payload'],'unchanged original full validator')
 supplement=module('literal_retained_executor_supplement',p['references']['executor_supplement']);supplement.check(m,receipt,data(p['references']['executor_contract']))
 loader=data(p['references']['loader_acceptance']);need(loader['status']=='ACTUAL_LOADER_COMPATIBILITY_PASS' and loader['actual_executor_sha256']==p['selected_executor']['sha256'] and loader['implementation_ownership'] is False,'actual matching installed loader')
 manifest_path=Path(p['expected_manifest']);binding_path=Path(p['expected_binding']);need(not manifest_path.exists() and not binding_path.exists(),'fresh finite binder outputs')
 with manifest_path.open('x') as f:json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
 mr=ref(manifest_path)
 # Original owner requires a scratch manifest, outside its real writable parent.
 # Root must first ordinary-stage byte-exact manifest to fresh scratch, then use
 # --check-existing-root-scratch-stage below. Never call owner API on REPO manifest.
 binding=dict(scope=p['scope'],status='ACTUAL_ROOT_COMPOSED_CORRECT_RUST_STARTUP_MANIFEST_BOUND_NOT_RUNTIME_RELEASE',manifest=mr,overlay=output,actual_receipt=r,collector=p['collector'],compiled_profile=p['compiled_collector_profile'],compiled_facts=p['compiled_collector_binding_facts'],Root_collector_adoption=p['references']['Root_collector_adoption'],normal_owner=p['references']['normal_owner'],diagnostic=p['references']['diagnostic'],loader_acceptance=p['references']['loader_acceptance'],current_free=None,current_ledger=None,nonce=None,source_authority=None,native_release=None,execution_authority=False,preserved_failure=p['preserved_failure'])
 with binding_path.open('x') as f:json.dump(binding,f,indent=2,sort_keys=True);f.write('\n')
 return binding

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--check-source',action='store_true');a.add_argument('--bind-existing-root-composition',action='store_true');a.add_argument('--check-existing-root-scratch-stage',action='store_true');a.add_argument('--receipt');a.add_argument('--receipt-sha256');a.add_argument('--scratch-manifest');a.add_argument('--scratch-manifest-sha256');a.add_argument('--attempt-parent');args=a.parse_args()
 need(sum([args.check_source,args.bind_existing_root_composition,args.check_existing_root_scratch_stage])==1,'one explicit data-only mode');p,facts,profile,d,o=source_check()
 if args.check_existing_root_scratch_stage:
  need(args.scratch_manifest and args.scratch_manifest_sha256 and args.attempt_parent,'actual Root ordinary scratch stage required')
  own=checked(ref(Path(p['expected_manifest'])));scratch=checked(dict(path=args.scratch_manifest,sha256=args.scratch_manifest_sha256));need(scratch==own,'Root scratch stage byteexact')
  o._manifest_identity(args.scratch_manifest,args.scratch_manifest_sha256);o._manifest_outside_writable_parent(args.scratch_manifest,args.attempt_parent);v=d.load_manifest(args.scratch_manifest);need(v['staging']['collector']==p['collector'],'qualified compiled collector preserved')
  print(json.dumps(dict(status='PASS_LITERAL_NORMAL_OWNER_MANIFEST_API_AFTER_ROOT_SCRATCH_STAGE_ONLY',manifest=ref(Path(args.scratch_manifest)),attempt_parent=args.attempt_parent,current_free=None,runtime_authority=None)));return
 if args.check_source:print(json.dumps(dict(status='PASS_COMPILED_STARTUP_PRODUCER_PROFILE_AND_LITERAL_OWNER_SOURCE_ONLY',collector=p['collector'],current_free=None,runtime_authority=None)));return
 need(args.receipt and args.receipt_sha256,'actual Root receipt required');print(json.dumps(bind(p,facts,profile,d,o,args.receipt,args.receipt_sha256)))
if __name__=='__main__':main()
