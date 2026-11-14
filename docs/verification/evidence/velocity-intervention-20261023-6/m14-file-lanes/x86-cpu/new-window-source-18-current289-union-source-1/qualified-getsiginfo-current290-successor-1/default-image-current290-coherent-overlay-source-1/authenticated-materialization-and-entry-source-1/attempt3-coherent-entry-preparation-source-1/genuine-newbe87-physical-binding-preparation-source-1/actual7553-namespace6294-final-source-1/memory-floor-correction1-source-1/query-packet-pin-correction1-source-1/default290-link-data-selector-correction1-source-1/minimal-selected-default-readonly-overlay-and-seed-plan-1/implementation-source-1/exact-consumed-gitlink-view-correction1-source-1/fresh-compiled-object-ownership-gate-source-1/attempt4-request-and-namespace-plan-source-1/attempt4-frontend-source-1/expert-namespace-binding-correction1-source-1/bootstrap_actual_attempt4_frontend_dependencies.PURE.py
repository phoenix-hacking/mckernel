"""Functional OS only; no security testing. Fixed actualfrontend module/file bootstrap; zeroqueries."""
import ast,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).parent
STATE=HERE/'COMPLETE-DEPENDENCY-CORRECTION1-BASE-STATE.SOURCE-ONLY.json'
def load(name,row):
 p=Path(row['path']);auth(row);spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def auth(row):
 p=Path(row['path']);raw=p.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=row['sha256'] or len(raw)!=row['bytes']:raise RuntimeError('bootstrapfilepin:'+str(p))
 return raw
def bootstrap():
 r=json.loads(STATE.read_bytes());origin=load('bootstrap_origin',r['origin_helper']);data=origin.data();fill=load('bootstrap_fill',r['fill']);caller=load('bootstrap_caller',r['caller']);cleanup=load('bootstrap_cleanup',r['cleanup']);protocol=cleanup.current230_contract();contract=protocol.contract();mode=load('bootstrap_mode',r['mode_adapter']);pure=mode.owner_module();seed=mode.seed_mounts(json.loads(auth(r['request'])))
 if hasattr(pure,'ImageOwner') or hasattr(pure,'main') or len(seed)!=9:raise RuntimeError('pure validator closure only')
 cfg=json.loads(auth(r['config']));origin.require_new_runtime_facts(cfg);origin.validate_source_origin(json.loads(auth(r['request'])),json.loads(auth(data['source_retention'])))
 if str(origin.DATA_BINDING)!=r['origin_data']['path'] or origin.DATA_BINDING_SHA!=r['origin_data']['sha256']:raise RuntimeError('origin DATA_BINDING completeconstantbinding')
 if str(fill.D)!=str(Path(r['caller']['path']).parent) or str(caller.D)!=str(Path(r['caller']['path']).parent):raise RuntimeError('actual copied module D')
 if str(caller.CONFIG)!=r['config']['path'] or caller.CONFIG_SHA!=r['config']['sha256']:raise RuntimeError('caller CONFIG constantbinding')
 if fill.ATTEMPT2_BINDING_HELPER!=r['origin_helper']:raise RuntimeError('fill sourceorigin constantbinding')
 if cleanup.CURRENT230_TYPED_PROTOCOL!=r['protocol'] or str(protocol.CONTRACT)!=r['contract']['path'] or protocol.CONTRACT_SHA!=r['contract']['sha256']:raise RuntimeError('cleanup/protocol constantbindings')
 if str(Path('/home/holden/mckernel')/cleanup.PUBLISHED_SCRIPT)!=r['cleanup']['path']:raise RuntimeError('cleanup PUBLISHED_SCRIPT')
 if str(cleanup.CURRENT230_CALLER_CAPTURE)!=cfg['capture_root']:raise RuntimeError('cleanup/caller capturebinding')
 refs=[r[k] for k in ('origin_data','origin_helper','physical','postjoin','physical_spec','physical_validator','mode_adapter','caller','config','fill','cleanup','protocol','contract','corrected_census_observer','five_capture','five_packet','actual_namespace_initialization','request','owner','driver','seed')]
 refs.append(dict(path=str(cleanup.FP_AUTHORITY),sha256=cleanup.FP_AUTHORITY_SHA,bytes=cleanup.FP_AUTHORITY.stat().st_size));refs.append(dict(path=str(cleanup.SELFTEST),sha256=hashlib.sha256(cleanup.SELFTEST.read_bytes()).hexdigest(),bytes=cleanup.SELFTEST.stat().st_size));refs.extend(protocol.required_static_references());refs.extend(cfg['pins'].values());refs.extend(cfg[k] for k in ('context_template','fill','physical','postjoin','publication','interpreter','taskset','namespace_initialization','source_origin_binding','new_post_shared_physical_consumer'))
 for slot in ('five_observations','prepare_metadata','finish_metadata','compact_census','owner_entry_unchanged'):
  source=cfg['commands'][slot].get('source')
  if source:refs.append(source)
  argv=cfg['commands'][slot].get('argv')
  if source and argv is not None and source['path'] not in argv:raise RuntimeError('actual command source/argv pair:'+slot)
 for key in ('current_request','published_origin_request','source_retention','full_source_manifest','source_materialization','source_copy_result','host_control_owner','image_entry_owner','driver','provenance','readonly_reuse_inputs','physical_consumer_spec','actual_physical','actual_postjoin','actual_namespace_initialization'):refs.append(data[key])
 for row in refs:auth(row)
 for path in (cleanup.ATTEMPT,cleanup.SHARED,cleanup.LEASE,cleanup.PLAN,cleanup.JOURNAL,cleanup.MUTEX,cleanup.CAPTURE,cleanup.QUARANTINE):
  if __import__('os').path.lexists(path):raise RuntimeError('future attempt4 actionpath unexpectedlypresent:'+str(path))
 if not cleanup.NAMESPACE.is_dir() or not cleanup.OUTPUT.is_dir() or not cleanup.EVIDENCE.is_dir():raise RuntimeError('genuine initializednamespace3 missing')
 for filename in fill.SOURCES:
  if not (Path(r['fill']['path']).parent/filename).is_file():raise RuntimeError('fill declared sibling missing:'+filename)
 packet=json.loads(auth(r['five_packet']));tree=ast.parse(packet['namespace_observation']['argv'][-1]);paths=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='paths' for v in n.targets)))
 if paths!=fill.EXPECTED_NAMESPACE:raise RuntimeError('all10namespaceARGV/constants exact')
 for row in (r['five_capture'],r['corrected_census_observer']):
  source=auth(row).decode();ast.parse(source)
  if row==r['five_capture'] and source.count(r['five_packet']['sha256'])!=2:raise RuntimeError('both five embedded packetpins')
  if row==r['corrected_census_observer'] and r['caller']['sha256'] not in source:raise RuntimeError('census callerchecksum')
 # Actual original69 validator and all69 authenticated source-origin files.
 fill.fetched(Path(fill.FETCHED_ORIGIN_PROOF['path']),fill.FETCHED_ORIGIN_PROOF['sha256'])
 selected={row['path']:cleanup.observe_identity(Path(row['path'])) for row in protocol.required_static_references()}
 protocol._static(selected)
 actual_chain=cleanup.namespace_ancestry()
 if actual_chain!=cleanup.NAMESPACE_ANCESTRY:raise RuntimeError('exact actual26baseparentchain')
 base_identity=next(row for row in r['actual_namespace_identities'] if row['path']==str(cleanup.NAMESPACE));expected_binding={key:base_identity[key] for key in ('device','inode','mode','uid','gid')};expected_binding['mode']|=0o40000
 if cleanup.NAMESPACE_BINDING!=expected_binding or actual_chain[-1]!=dict(path=str(cleanup.NAMESPACE),**expected_binding):raise RuntimeError('actualbase333binding, neverlastreceiptparent')
 obs={'candidate_root':cleanup.observe_identity(Path(data['source_identity']['path'])),'namespace_binding':cleanup.NAMESPACE_BINDING}
 protocol.typed_source_binding(json.loads(auth(r['request'])),obs,selected)
 return dict(state=r,origin=origin,data=data,fill=fill,caller=caller,cleanup=cleanup,protocol=protocol,mode=mode,pure=pure,selected=selected,typed_source_observation=obs,authenticated_reference_count=len({row['path'] for row in refs}))
