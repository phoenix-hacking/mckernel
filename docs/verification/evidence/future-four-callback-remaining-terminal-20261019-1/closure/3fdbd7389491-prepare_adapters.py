"""Source-only binding of accepted engine functions to this future namespace."""
from pathlib import Path
import ast,hashlib,json
T=Path(__file__).resolve().parent;N=T.parent
OLD=Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1')
OT=OLD/'heavy-proposal-1/terminal-preparation-1';C1=OT/'observer-cardinality-correction-1'
P=json.loads((N/'postbuild-inputs.json').read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def rebind(path,values,target):
 source=path.read_text();tree=ast.parse(source);lines=source.splitlines(True);replacements=[]
 for node in tree.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   name=node.targets[0].id;v=values[name];text='Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v)
   replacements.append((node.lineno-1,node.end_lineno,name+' = '+text+'\n'))
 assert {name for name in values}=={lines[a].split('=')[0].strip() for a,b,text in replacements}
 for a,b,text in sorted(replacements,reverse=True):lines[a:b]=[text]
 target.write_text(''.join(lines))
 # Accepted engine function ASTs must remain byte-for-byte AST equivalent.
 before=[ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
 after=[ast.dump(n,include_attributes=False) for n in ast.parse(target.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
 assert before==after
 return dict(base=ref(path),bound=ref(target),function_AST_unchanged=True,changed_globals=sorted(values))
rows=json.loads(Path(P['retention']['role_source']['path']).read_text());assert len(rows)==21
roles={}
for row in rows:
 original=row['original']['path'].replace(str(OLD),str(N),1)
 retained=row['retained'].replace(str(OT),str(T),1).replace(str(OLD),str(N),1)
 roles[row['kind']]=dict(action=row['action'],original=original,retained=retained)
write(T/'future-role-paths.json',roles)
retention_source=OT/'retention_observer21.py'
proofs=[rebind(retention_source,{'ARTIFACT_PATHS':roles},T/'retention_observer21.py')]
nonce='future-four-callback-observation-1';output=T/('root-observation-'+nonce)
proofs.append(rebind(C1/'readback_observer.py',{'OUTPUT':output,'NONCE':nonce},T/'readback_observer.py'))
# Metadata helper and export are exact accepted C1 code with their summary/output
# references rebound. No genuine original hashes or root observations exist yet.
for name in ['read_original_five_metadata.py','export_raw_five.py']:
 source=C1/name;tree=ast.parse(source.read_text());assigns={n.targets[0].id for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
 candidate={'SUMMARY':T/'readback_observer.py','SUMMARY_SHA':ref(T/'readback_observer.py')['sha256'],'OUTPUT':output}
 values={k:v for k,v in candidate.items() if k in assigns};assert values
 proofs.append(rebind(source,values,T/name))
write(T/'accepted-engine-specializations.json',proofs)
# Genuine build/CID/owner/boot/artifact fields are supplied only to the late
# configuration adapter, never copied from the accepted predecessor.
engines={k:P['retention'][k] for k in ('accepted_engine','accepted_join')}
engines.update(observer=P['terminal']['corrected_observer'],cleanup=P['terminal']['cleanup_engine'])
engines.update(facts=ref(OLD/'postbuild-consumer-v2/postbuild_four_leaf_facts_v2.py'),retention_observer=ref(T/'retention_observer21.py'),summary=ref(T/'readback_observer.py'),metadata=ref(T/'read_original_five_metadata.py'),raw_export=ref(T/'export_raw_five.py'))
source_doc=json.loads((N/'heavy-proposal-1/source-sha256.json').read_text());source11=source_doc['source_sha256'];assert len(source11)==11
closure=dict(source11)
for row in json.loads((OT/'terminal-publication-closure-final.json').read_text())['rows']:closure[row['path']]=row['sha256']
for value in engines.values():closure[value['path']]=value['sha256']
extra=source_doc['additional_dispatcher'];closure[extra['path']]=extra['sha256']
for name in ['terminal_contract.py','postbuild_future_facts.py','prepare_adapters.py']:
 r=ref(T/name);closure[r['path']]=r['sha256']
request=json.loads((N/'image-request.json').read_text())
known=dict(schema='mckernel.future-four-callback.known-terminal-source-inputs.v1',implementation_author='next_live_process_rust_batch',implementation_ownership=True,root_or_cleanup_authority=False,request=dict(path=str(N/'image-request.json'),sha256='e9497da4204aed95708bb0f2ceb062a88c45517c13e3c69e65510fb59334cec0'),source_identity=request['source_identity'],source11=source11,full_import_closure=closure,source11_authority=ref(N/'heavy-proposal-1/source-sha256.json'),engines=engines,numeric_caps=dict(metadata_bytes=128<<20,per_stream_bytes=32<<20,total_capture_bytes=128<<20,inventory_entries=400000,pair_count=len(roles),source_count=len(source11)),postbuild_contract=ref(N/'postbuild-inputs.json'),future_roles=ref(T/'future-role-paths.json'),observation_nonce=nonce,five_original_names=['ownership.json','new-object-metadata.json','observation.json','cleanup-release-draft.json','observer-result.json'],cleanup_canonical='JSON_SORTED_COMPACT_NO_NEWLINE',pending_genuine=['successful_actual_build','actual_guard_owner_CID_and_boot','actual_artifact_FD_pairs','actual15_capture_completion','late_actual_Rust_Ndx_and_linked_addresses','actual_root_five_FD_metadata_and_distinct_summaries'])
write(T/'known-terminal-inputs.json',known)
print('PREPARED exact21 roles/source11/full closure;4 unchanged-function engine specializations;genuine build facts pending')
