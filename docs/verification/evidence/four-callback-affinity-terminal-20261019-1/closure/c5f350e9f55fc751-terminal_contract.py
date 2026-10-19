"""Finite future-four-callback joins; no root, Docker, copy, or cleanup effects."""
from pathlib import Path
import hashlib,json,os,stat,types

NAMES=('ownership.json','new-object-metadata.json','observation.json','cleanup-release-draft.json','observer-result.json')
FD_FIELDS=('path','device','inode','mode','uid','gid','size','nlink','mtime_ns','ctime_ns','sha256')
AUTHOR='next_live_process_rust_batch'

def need(ok,why):
 if not ok:raise ValueError(why)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def cleanup_canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def line_canonical(value):return cleanup_canonical(value)+b'\n'
def exact_int(value,lo,hi,name):
 need(type(value) is int and lo<=value<=hi,'numeric bound:'+name);return value

def checked_bytes(ref,maximum=16<<20):
 need(set(ref)>={'path','sha256'} and isinstance(ref['sha256'],str) and len(ref['sha256'])==64,'exact byte reference')
 path=Path(ref['path']);need(path.is_absolute() and path.resolve()==path,'exact absolute source path')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=maximum,'bounded regular source')
  with os.fdopen(os.dup(fd),'rb') as f:raw=f.read(before.st_size+1)
  after=os.fstat(fd);named=path.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')),'stable source FD')
  need(len(raw)==before.st_size and digest(raw)==ref['sha256'],'source digest')
  return raw
 finally:os.close(fd)

def checked_module(ref,name):
 raw=checked_bytes(ref);m=types.ModuleType(name);m.__file__=ref['path'];exec(compile(raw,m.__file__,'exec'),m.__dict__);return m

def validate_known(known):
 need(known['implementation_author']==AUTHOR and known['implementation_ownership'] is True,'explicit implementation author')
 need(known['root_or_cleanup_authority'] is False,'preparation grants no execution')
 caps=known['numeric_caps']
 for k in ('metadata_bytes','per_stream_bytes','total_capture_bytes','inventory_entries','pair_count','source_count'):
  exact_int(caps[k],1,1<<30,k)
 need(caps['pair_count']==21 and caps['source_count']==11,'finite role/source contract')
 need(caps['metadata_bytes']<=128<<20 and caps['per_stream_bytes']<=32<<20,'reviewed byte ceilings')
 need(known['source_identity']['dev']==66306 and known['source_identity']['inode']==48005996,'actual materialized source identity')
 need(known['request']['sha256']=='e9497da4204aed95708bb0f2ceb062a88c45517c13e3c69e65510fb59334cec0','actual future request binding')
 source11=known['source11'];need(isinstance(source11,dict) and len(source11)==11,'known source11 required now')
 closure=known['full_import_closure'];need(isinstance(closure,dict) and set(source11)<=set(closure),'full import closure covers source11')
 for path,sha in closure.items():checked_bytes(dict(path=path,sha256=sha),caps['metadata_bytes'])
 for ref in known['engines'].values():
  need(closure.get(ref['path'])==ref['sha256'],'engine included in full import closure')
 return known

def validate_pairs(pairs,roles):
 need(isinstance(pairs,list) and len(pairs)==len(roles)==21,'actual finite21 pairs')
 need(len(set(roles))==len(roles),'unique role names')
 out={};seen=set()
 for pair in pairs:
  need(set(pair)=={'original','retained','outside_generic_receipt_inventory'} and pair['outside_generic_receipt_inventory'] is True,'producer pair schema')
  a,b=pair['original'],pair['retained'];key=(a['path'],b['path'])
  need(key not in seen,'duplicate pair');seen.add(key)
  need(a['sha256']==b['sha256'] and a['size']==b['size'] and a['nlink']==b['nlink']==1,'same-byte single-link pair')
  need((a['device'],a['inode'])!=(b['device'],b['inode']),'independent retained file')
  matches=[role for role,paths in roles.items() if paths==dict(original=a['path'],retained=b['path'])]
  need(len(matches)==1,'exact role paths');out[matches[0]]=pair
 need(set(out)==set(roles),'complete exact roles');return out

def validate_pair_fd_rows(pairs,roles,rows):
 validate_pairs(pairs,roles)
 # Cardinality derives from ACTUAL pairs. No historical 29/58 assumption.
 need(isinstance(rows,list) and len(rows)==2*len(pairs),'two original/retained FD rows per pair')
 expected=[pair[side] for pair in pairs for side in ('original','retained')]
 need(len({row['path'] for row in rows})==len(rows),'unique FD rows')
 bypath={row['path']:row for row in rows}
 for row in expected:
  need(row['path'] in bypath,'missing FD path');fresh=bypath[row['path']]
  need(all(fresh[k]==row[k] for k in FD_FIELDS),'complete original FD identity differs')
 return len(rows)

def validate_raw_five(raw,metadata,observer_summary,readback_summary,pairs,roles):
 need(set(raw)==set(NAMES) and len(metadata)==len(NAMES),'five original files and FD metadata')
 need(observer_summary is not readback_summary and observer_summary.get('role')=='OBSERVER_RESULT' and readback_summary.get('role')=='RAW_FIVE_READBACK','distinct observer/readback summaries')
 need(len({m['path'] for m in metadata})==len(metadata),'unique original metadata paths')
 byname={Path(m['path']).name:m for m in metadata};need(set(byname)==set(NAMES),'exact original names')
 for name,content in raw.items():
  m=byname[name];need(type(content) is bytes and m['sha256']==digest(content) and m['size']==len(content),'original FD hash/bytes')
  need(m['uid']==0 and m['nlink']==1 and m['mode'] in ('0o600',384),'root original single-link regular mode')
  for key in FD_FIELDS:need(key in m,'complete original metadata:'+key)
 result=json.loads(raw['observer-result.json']);observation=json.loads(raw['observation.json']);draft=json.loads(raw['cleanup-release-draft.json']);objects=json.loads(raw['new-object-metadata.json'])
 need(result['status']=='PASS_READ_ONLY_OBSERVATION_ONLY' and result['cleanup_executed'] is False,'read-only observer result')
 need(result['observation_sha256']==digest(raw['observation.json']) and result['cleanup_release_draft_sha256']==digest(raw['cleanup-release-draft.json']),'raw observer joins')
 need(draft['status']=='NOT_RELEASED' and draft['observation']==observation,'unreleased exact observation')
 # Cleanup engine signs canonical JSON WITHOUT a newline; raw-five files retain
 # their actual bytes and are hashed independently, including any final newline.
 canonical_hash=digest(cleanup_canonical(observation))
 need(readback_summary['observation_canonical_sha256']==canonical_hash,'cleanup no-newline canonical join')
 need(observer_summary['observer_result_sha256']==digest(raw['observer-result.json']) and readback_summary['observer_result_sha256']==digest(raw['observer-result.json']),'two summary joins')
 count=validate_pair_fd_rows(pairs,roles,objects['objects'])
 need(readback_summary['original_fd_metadata_sha256']==digest(line_canonical(metadata)),'all five original FD metadata join')
 return dict(pair_count=len(pairs),fd_rows=count,original_files=len(raw),cleanup_canonical_sha256=canonical_hash)

def bind_engine_config(known,late):
 validate_known(known)
 required=('boot_id','container_id','owner_nonce','physical_join','pairs','roles','original_five','artifact_report','publication')
 need(all(k in late and late[k] is not None for k in required),'genuine build/owner/artifact facts pending')
 need(len(late['container_id'])==64 and all(c in '0123456789abcdef' for c in late['container_id']),'genuine container identity')
 frozen_roles=json.loads(checked_bytes(known['future_roles']));expected_roles={k:{x:v[x] for x in ('original','retained')} for k,v in frozen_roles.items()}
 need(late['roles']==expected_roles,'exact frozen future roles')
 validate_pairs(late['pairs'],late['roles'])
 need(late['publication']['implementation_author']==AUTHOR and late['publication']['reviewer']!=AUTHOR,'independent final execution release')
 return dict(schema='mckernel.future-four-callback.terminal-engine-config.v1',implementation_author=AUTHOR,known=known,actual=late,expected_metadata_rows=2*len(late['pairs']),engine_sources=known['engines'],cleanup_canonical='JSON_SORTED_COMPACT_NO_NEWLINE',root_or_cleanup_authority=False)

def validate_future_canonical_report(report,additive,completion_sha256,additive_sha256):
 need(report.get('schema')=='mckernel.independent-rust-four-leaf-image-actual-review.v1' and report.get('decision')=='PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT','existing canonical schema with explicit future scope')
 need(additive.get('schema')=='mckernel.future-four-callback.postbuild-additive-facts.v1' and additive.get('status')=='PASS_ADDITIVE_MECHANICAL_FACTS_ONLY','additive future proof required')
 need(additive['old_four_leaf_facts']['status']=='PASS_OLD_FOUR_LEAF_MECHANICAL_FACTS_FROM_THIS_FIFTEEN_CAPTURE_SET','same-image old-four proof')
 expected=dict(zip(('process_current_resource_set_bridge','process_release_hash_detach_bridge','process_release_sibling_detach_bridge','process_release_final_cleanup_bridge'),(8,9,10,17)))
 rows=additive['callbacks'];need(len(rows)==len(expected) and {r['symbol']:r['argument_index_from_frozen_Rust_source'] for r in rows}==expected,'explicit four future callback proof vectors')
 need(report['future_four_callbacks']['additive_facts_sha256']==additive_sha256 and report['future_four_callbacks']['completion_sha256']==completion_sha256,'canonical additive proof and actual completion binding')
 need(report['future_four_callbacks']['argument_index_convention']=='zero-based-body-result-argument','source argument convention')
 need(additive['production_or_native_acceptance'] is False,'facts are not native acceptance')
 return True
