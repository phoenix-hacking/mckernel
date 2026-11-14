"""Exact remaining9f04 path specialization; no build, root or cleanup effects."""
from pathlib import Path
import ast,json
from terminal_contract import checked_bytes,need

def actual_request(known):
 request=json.loads(checked_bytes(known['request'],64<<20))
 need(request['source_root']==known['remaining_output_paths']['source_root'],'frozen original materialized source')
 for key in ('work_root','owner_evidence_root','output_root','evidence_root','attempt_root','lease_path','common_exclusion_path'):
  need(request[key]==known['remaining_output_paths'][key],'actual remaining path '+key)
 sources=known['remaining_control_plane']['sources'];driver=next((r for r in sources.values() if r['path']==request['driver_path']),None)
 need(driver is not None and driver['sha256']==request['driver_sha256'],'remaining driver source join')
 return request

def specialize_cleanup_source(source,known):
 request=actual_request(known)
 old="NAMESPACE / 'materialized-source' if key == 'source_root' else ROOT / 'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'"
 new="Path("+repr(request['source_root'])+") if key == 'source_root' else ROOT / 'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'"
 need(source.count(old)==1,'single exact source-root premise');source=source.replace(old,new)
 values=dict(IMAGE_CANDIDATE=request['candidate_sha'],PREFIX='future-four-callback-remaining-terminal-20261019-1',PUBLISHED_SCRIPT='docs/verification/evidence/future-four-callback-remaining-terminal-20261019-1/cleanup_fourleaf.py')
 lines=source.splitlines(keepends=True)
 for node in sorted(ast.parse(source).body,key=lambda n:n.lineno,reverse=True):
  if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   key=node.targets[0].id;lines[node.lineno-1:node.end_lineno]=[key+' = '+repr(values[key])+'\n']
 return ''.join(lines)

def specialize_observer_source(source,known):
 request=actual_request(known)
 old="selected_paths.update((FULL_SOURCE_MAP_PATH,CASE/'gitlink-inputs.json',CASE/'image-toolchain.json',CASE/'materialization-receipt.json',CASE/'thin-inputs.json'))"
 paths=[known['source11_authority']['path'],request['gitlink_manifest'],request['toolchain_manifest'],known['materialization_receipt']['path'],request['source_manifest'],known['remaining_control_plane']['source_map']['path']]
 control={row['path']:row['sha256'] for row in known['remaining_control_plane']['sources'].values()}
 for row in known['remaining_control_plane']['unchanged_accepted_imports']:control[row['path']]=row['sha256']
 replacement='selected_paths.update(Path(p) for p in '+repr(sorted(set(paths)|set(control)))+')'
 need(source.count(old)==1,'single exact source-input path set');source=source.replace(old,replacement)
 old="need(selected_map[str(FULL_SOURCE_MAP_PATH)]['sha256']==FULL_SOURCE_MAP_SHA,'actual full11 source map descriptor differs')"
 replacement=old+'\n        need(all(selected_map[p][\'sha256\']==h for p,h in '+repr(control)+'.items()),\'remaining control-plane source bytes differ\')'
 need(source.count(old)==1,'single source descriptor check');source=source.replace(old,replacement)
 source=source.replace("NONCE = 'four-leaf-observation-actual-1'","NONCE = 'future-four-callback-remaining-observation-1'")
 return source
