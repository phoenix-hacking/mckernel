"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual changed BODY5 uses its banked tested source contract, not old116 byte equality.
"""
from pathlib import Path
import ast,json,hashlib
p=Path(__file__).resolve().parent/'inspect_conversion.py';nodes=[]
for node in ast.parse(p.read_bytes()).body:
 if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='proofs'for t in node.targets):break
 nodes.append(node)
ns={'__file__':str(p)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':READONLY_CONTEXT_ONLY','exec'),ns);globals().update(ns)
packet=E/'m14-f03-next-runtime-body5-restart-20261028-1';ready=read(packet/'SOURCE-READY.json');candidate=next(row for row in ready['files']if row['path'].endswith('/allocator-candidate.Rust.inc'));text=auth(candidate).read_text()
manifest=read(auth(profile['inputs']['source_directory_exports'][0]['manifest']));selected=next(row['snapshot']for row in manifest['files']if row['relative']=='syscall_policy.rs');actualsource=auth(selected).read_text();assert ''.join(text.split())in''.join(actualsource.split())
qualification=read(packet/'fixture-header-correction-1/output-header-correction-1/ACTUAL-HOST-RESULT.json');assert all(c['returncode']==0 and c['positive_wait4_join']for c in qualification['commands']);behavior=qualification['commands'][1];stdout=auth(behavior['stdout_record']).read_text()
name='perf_event_alloc_map_body_result';s,raw,tokens,records=relocated_function(new,name,image);before,br,bt,_=relocated_function(old,name);assert raw!=br or tokens!=bt
result=dict(scope=__doc__.splitlines()[0],status='PASS_QUALIFIED_CHANGED_BODY5_SOURCE_AND_ACTUAL119_FINAL_READBACK_PENDING_INDEPENDENT_REVIEW',name=name,actual_Rust=ref(new.path),actual_image=ref(image.path),actual_function=s,final_function=image.sym(name),full_final_bytes_and_all_relocations_reproduced=True,actual_relocations=records,source_candidate=candidate,actual_compiled_source_snapshot=selected,tested_candidate_tokens_exact_in_actual_compiled_source=True,qualified_HOST_result=ref(packet/'fixture-header-correction-1/output-header-correction-1/ACTUAL-HOST-RESULT.json'),qualified_HOST_stdout=behavior['stdout_record'],qualified_behavior_output=stdout,expected_changed_from116=True,disposition='F03BODY5 intentionally moves cacheevent initialization before cacheextra-map provider, exact previouslyqualified BODY5 source tokens and behavior reused. Do not require old116 unchanged-byte equality for this declared source change. Actualnewproduction function reconstructed exactly in final119image. No HOSTobject machinecode equivalence claimed across Rust1.92/nightly1.95 flags.',no_new_HOST_or_compiler_execution=True,artifact_acceptance=False,native_acceptance=False,wholefile_acceptance=False,runtime_authority=None)
(D/'QUALIFIED-BODY5-ACTUAL119-READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],qualified_behavior=stdout,report=ref(D/'QUALIFIED-BODY5-ACTUAL119-READBACK.json'))))
