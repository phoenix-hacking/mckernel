"""One fixed NEW205 report consumer; no caller-selected schema or PASS label."""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,sys
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T))
from case_contract import checked_bytes,need,validate_pairs,validate_pair_fd_rows
CONTRACT=dict(path='/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-heavy-review-20261019-1/NEW205-CANONICAL-REPORT-FIXED-CONTRACT-v2.json',sha256='56a54c83f7049188650a4afc37ef66ad1ee172f67b709fefe6037c449abd64a8')
ROLE_SOURCE=dict(path=str(T.parent/'postbuild-preparation-1/retention-role-paths.json'),sha256='a0e64f5afe0e1583135113252b2a7076c89e12280a2a8e6e0722b4f92c7fe363')
ENGINE=dict(path='/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retention-engine-frozen.py',sha256='c6fdfc96dfcfd4c78888335625f68092cf39b1b6c3158dc367f8a1321cebd90b')
JOIN = {'path': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained_join.py', 'sha256': '068bcea5a75fe23f737fb8cc44041dbc010cb064aa042075f4fd03cce5584208'}
ACTUAL_RETENTION_INTERFACE=dict(path='/home/holden/mckernel-work/host-preparation/four-callback-affinity-terminal-adapter-independent-review-20261019-1/ACTUAL37-RETENTION-ACCEPTANCE-INTERFACE.json',sha256='672f0e291b26773baad1d39c2fa79d362be35de642fbcb07145b58a697510ca4')
def reference_shape(ref):
 need(isinstance(ref,dict) and set(ref)=={'path','sha256','bytes'},'exact declared reference fields')
 need(isinstance(ref['path'],str) and Path(ref['path']).is_absolute() and isinstance(ref['sha256'],str) and len(ref['sha256'])==64 and all(x in '0123456789abcdef' for x in ref['sha256']),'declared reference path/hash type')
 need(type(ref['bytes']) is int and ref['bytes']>=0,'declared reference nonboolean byte count')
 return ref

def read_reference(ref,maximum=4<<20):
 reference_shape(ref);need(ref['bytes']<=maximum,'declared reference byte ceiling')
 raw=checked_bytes(ref,maximum);need(len(raw)==ref['bytes'],'declared reference actual byte count');return raw

def reference_metadata_tree(value):
 # Ref3 metadata is checked without rehashing unrelated compiler/capture
 # corpora. Consumed JSON refs below additionally hash the same read snapshot.
 if isinstance(value,dict):
  if 'path' in value and 'sha256' in value and ('bytes' in value or 'size' not in value):
   reference_shape(value);p=Path(value['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   try:
    a=os.fstat(fd);b=os.fstat(fd);n=p.lstat();fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size==value['bytes'] and all(getattr(a,k)==getattr(b,k)==getattr(n,k) for k in fields),'declared reference stable actual byte count')
   finally:os.close(fd)
  else:
   for child in value.values():reference_metadata_tree(child)
 elif isinstance(value,list):
  for child in value:reference_metadata_tree(child)

def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate_fourleaf_authority(binding):
 contract=json.loads(checked_bytes(CONTRACT));actual=binding['canonical_report'];need(actual['path']==contract['actual_report_path'],'fixed independent NEW205 report path')
 report=json.loads(read_reference(actual,4<<20));reference_metadata_tree(report);need(set(report)==set(contract['required_top_level_fields']),'complete fixed NEW205 report fields')
 need(report['schema']==contract['report_schema_literal'] and report['decision']==contract['report_decision_literal'] and report['status']==contract['report_status_literal'],'literal independent NEW205 artifact authority')
 need(report['phase_status']==contract['phase_status_literals'],'individual fresh compiler/image/facts/retention phases')
 need(all(report[k] is v for k,v in contract['acceptance_bits'].items()),'actual artifact only, no native/compute retirement')
 need(report['reviewer'] and report['reviewer']!='next_live_process_rust_batch','independent actual report')
 for name in ('request','manifest','materialization_receipt'):
  read_reference(report['source_request_bindings'][name],64<<20 if name=='request' else 8<<20 if name=='manifest' else 4<<20)
  need(report['source_request_bindings'][name]==report['source_authority'][name]==contract['source_authority'][name],'actual source request alias:'+name)
 for name in ('source_identity','candidate_sha','candidate_identity_scope','ihk_sha','source_derivative_sha256','materialization_sha256','code_checkpoint','actual_file_pins'):
  need(report['source_authority'][name]==contract['source_authority'][name],'frozen fresh205 source:'+name)
 need(set(report['source11'])>=set(contract['source11']['required_fields']),'complete source11 lineage')
 for name in ('authority','publication'):
  need(report['source11'][name]==contract['source11'][name],'exact source11 lineage:'+name)
 source11=report['source11'];source_wrapper=json.loads(read_reference(contract['source11']['authority']));smap=source_wrapper['source_sha256']
 need(isinstance(smap,dict) and len(smap)==contract['source11']['count'] and all(isinstance(p,str) and Path(p).is_absolute() and isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h) for p,h in smap.items()),'actual typed source11 authority map')
 need(source11['source_sha256']==smap and type(source11['count']) is int and source11['count']==len(smap),'complete actual source11 map/count')
 request=json.loads(read_reference(contract['source_authority']['request'],64<<20))
 for name in ('declared_host_owner','executed_image_owner','guard'):
  r=source11[name];need(r['path'] in smap and r['sha256']==smap[r['path']],'source11 member:'+name);read_reference(r)
 need(source11['declared_host_owner']['path']==request['host_owner_path'] and source11['declared_host_owner']['sha256']==request['host_owner_sha256'],'actual declared lower host owner')
 need(source11['executed_image_owner']['path']==str(T.parent/'adapters/native_rust_exact_mckernel_image_container_owner.py'),'actual full image owner wrapper')
 guardpaths=[p for p in smap if 'guard' in Path(p).name];need(len(guardpaths)==1 and source11['guard']['path']==guardpaths[0],'actual corrected guard source')
 lineage=source11['request_lineage'];gr=report['guard_retirement'];need(set(lineage)=={'request','owner_receipt','driver_receipt','guard_result','postjoin_readback'},'explicit actual request/client lineage')
 need(lineage['request']==report['source_authority']['request'] and lineage['driver_receipt']==report['compiler_proofs']['driver_receipt'] and all(lineage[k]==gr[k] for k in ('owner_receipt','guard_result','postjoin_readback')),'same new205 runtime lineage')
 role_doc=json.loads(checked_bytes(ROLE_SOURCE));roles={r['role']:r for r in role_doc['roles']};authority=report['retained_authority'];need(set(authority)==set(contract['retained_authority']['exact_fields']),'fixed retained authority fields')
 need(all(type(authority[k]) is int for k in ('role_count','copy_count','reuse_count','metadata_rows')) and authority['role_count']==len(roles) and authority['copy_count']==sum(r['action']=='copy' for r in roles.values()) and authority['reuse_count']==sum(r['action']=='reuse' for r in roles.values()) and authority['metadata_rows']==2*len(roles),'derived bound role cardinalities')
 need(len(authority['original_authorities'])==len(authority['pairs'])==len(roles),'complete actual original/retained roles')
 need(sum(r['original']['size'] for r in authority['pairs'])<=role_doc['finite_retention_planning_maximum_bytes'],'finite bound retained bytes')
 originals={r['kind']:r for r in authority['original_authorities']};pairs={r['kind']:r for r in authority['pairs']};need(set(originals)==set(pairs)==set(roles),'exact role set')
 checked_bytes(ENGINE);engine=load(Path(ENGINE['path']),'_new205_retention_engine');checked_bytes(JOIN);join=load(Path(JOIN['path']),'_new205_retained_join');raw=json.loads(read_reference(authority['objects_manifest']));need(len(raw)==len(roles),'actual raw engine pairs')
 fields=set(contract['engine_full_FD_type']['exact_fields']);projected=[]
 for kind,role in roles.items():
  a=originals[kind];p=pairs[kind];need(a['action']==p['action']==role['action'] and a['retained']==role['retained_path'] and a['original']['path']==role['original_path'],'bound original action/paths')
  need(p['original']==a['original'] and p['retained']['path']==role['retained_path'],'same full original authority')
  for d in (p['original'],p['retained']):need(set(d)==fields and isinstance(d['mode'],str) and d['mode'].startswith('0o') and oct(int(d['mode'],8))==d['mode'] and all(type(d[k]) is int for k in ('device','inode','uid','gid','size','mtime_ns','ctime_ns','nlink')),'complete engine FD types')
  pair=dict(original=p['original'],retained=p['retained'],outside_generic_receipt_inventory=True);need(raw.count(pair)==1,'exact same raw engine pair')
  if role['action']=='reuse':need(a['retained_authority']==p['retained'],'full typed primary reuse authority')
  need(join.join_one(engine,p['retained'])==p['retained'],'actual retained held-FD bytes/identity');projected.append(pair)
 validate_pairs(projected,{k:dict(original=r['original_path'],retained=r['retained_path']) for k,r in roles.items()})
 terminal=json.loads(read_reference(authority['engine_result']));need(terminal['status']=='PASS_FINITE_EXACT_RETENTION_ONLY' and terminal['pairs']==len(roles),'actual finite engine result')
 interface=json.loads(checked_bytes(ACTUAL_RETENTION_INTERFACE));review=json.loads(read_reference(authority['independent_review']));reference_metadata_tree(review)
 need(all(review.get(k)==v for k,v in interface['future_actual_review_literals'].items()),'literal successful actual37 retention disposition')
 need(review.get('implementation_ownership') is False and isinstance(review.get('reviewer'),str) and review['reviewer'] and review['reviewer']!='next_live_process_rust_batch','independent actual retention acceptance')
 need(all(type(review.get(k)) is int and review[k]==n for k,n in [('pairs',len(roles)),('copy_pairs',authority['copy_count']),('reuse_pairs',authority['reuse_count'])]),'actual37 retention review counts')
 need(review.get('retained_objects')==authority['objects_manifest'] and review.get('retention_result')==authority['engine_result'],'actual37 review binds objects and result')
 need(all(review.get(k) is False for k in ('cleanup_authorized','physical_release','native_acceptance','production_artifact_acceptance')),'retention acceptance grants preservation only')
 need(isinstance(review.get('actual_FD_rows'),list) and all(set(r)==fields and all(type(r[k]) is int for k in ('device','inode','uid','gid','size','mtime_ns','ctime_ns','nlink')) for r in review['actual_FD_rows']),'actual37 review full FD types')
 validate_pair_fd_rows(projected,{k:dict(original=r['original_path'],retained=r['retained_path']) for k,r in roles.items()},review.get('actual_FD_rows'))
 primary=report['existing_primary_pairs'];need(type(primary['count']) is int and primary['count']==len(report['actual_artifacts'])==sum(r['action']=='reuse' for r in roles.values()),'actual four primary pairs')
 need(set(report['actual_artifacts'])==set(contract['actual_artifacts']['exact_roles']) and len(primary['pairs'])==primary['count'],'exact four primary artifact roles')
 need({p['role'] for p in primary['pairs']}==set(report['actual_artifacts']) and len({p['original']['path'] for p in primary['pairs']})==primary['count'] and len({p['retained']['path'] for p in primary['pairs']})==primary['count'],'unique exact primary roles/source/destination paths')
 copier=json.loads(read_reference(primary['copier_receipt']));need(copier.get('status')=='PASS_EXACT_FOUR_ARTIFACT_RETENTION_ONLY' and set(copier.get('artifacts',{}))==set(report['actual_artifacts']),'actual exact four-primary copier receipt')
 for pair in primary['pairs']:
  need(pair['role'] in report['actual_artifacts'] and report['actual_artifacts'][pair['role']]==pair['original'],'primary report original fullFD')
  matches=[p for p in pairs.values() if p['action']=='reuse' and p['original']==pair['original'] and p['retained']==pair['retained']]
  need(len(matches)==1,'exact primary same-FD reuse join')
  original,retained=pair['original'],pair['retained'];converted=dict(original);converted['dev']=converted.pop('device');converted['bytes']=converted.pop('size');converted['mode']=int(converted['mode'],8);converted.pop('nlink');copy=copier['artifacts'][pair['role']]
  need(copy['source']==converted and copy['retained_path']==retained['path'] and copy['retained_dev']==retained['device'] and copy['retained_inode']==retained['inode'] and copy['bytes']==retained['size'] and copy['sha256']==retained['sha256'] and all(original[k]==retained[k] for k in ('size','sha256','uid','gid','mode')),'actual copier source conversion and retained-FD join')
 for name in ('compiler_proofs','affinity_default_witnesses','postbuild_facts'):
  need(set(report[name])>=set(contract[name]['required_fields']),'explicit actual proof block:'+name)
 need(report['compiler_proofs']['no_old_compiled_artifacts_adopted'] is True,'fresh complete compilers, no adopted prefix')
 need(set(report['four_callback_witnesses'])>=set(contract['four_callback_witnesses']['required_exports']),'four actual default callback witnesses')
 return actual
