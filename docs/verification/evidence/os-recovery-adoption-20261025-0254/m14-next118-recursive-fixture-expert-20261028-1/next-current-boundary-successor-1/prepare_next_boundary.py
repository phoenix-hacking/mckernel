"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse the reviewed118 source renderer, then apply narrow typed boundary/count/row fixes.
Private source output only; no actual runtime DATA/export/guard/capture/build.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
E=HERE.parent.parent
RENDERER=E/'m14-next118-composition-restart-20261028-1/cohort-successor-1/recursive-routing-correction-1/prepare_routing.py'


def ref(p):
    p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def write(p,value):
    with Path(p).open('x')as out:json.dump(value,out,indent=2,sort_keys=True);out.write('\n')


def prepare(destination):
    assert ref(RENDERER)['sha256']=='63061f77d27bfc0c81188312628923fe6fe27afd6fb348db6220fdfdeadb1086'
    spec=importlib.util.spec_from_file_location('unchanged_corrected118_source_renderer',RENDERER)
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    layout=p.prepare(destination);root=layout['root'];cohort=layout['cohort'];changes=[]
    (root/'EXACT-SOURCE-DELTAS.json').rename(root/'EXACT-SOURCE-DELTAS.RETAINED-RENDERER.json')
    # All core behavior is independently visible in this sibling source module.
    (root/'typed_current_boundary.py').write_bytes((HERE/'typed_current_boundary.py').read_bytes())
    (root/'UPSTREAM-SELECTION.SOURCE-ONLY.json').write_bytes((HERE/'UPSTREAM-SELECTION.SOURCE-ONLY.json').read_bytes())
    core=ref(root/'typed_current_boundary.py');selection=ref(root/'UPSTREAM-SELECTION.SOURCE-ONLY.json')
    observer=root/'observe_current63_current118.py'
    text='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No-argument118 interface to separately accepted post-BFD current63; no old-free fallback.
"""
from pathlib import Path
import importlib.util,json
CORE=CORE_LITERAL
SELECTION=SELECTION_LITERAL
BINDING=Path(__file__).resolve().parent/'ROOT-CURRENT118-TYPED-BOUNDARY.json'
def _core():
 raw=Path(CORE['path']).read_bytes()
 import hashlib
 assert len(raw)==CORE['bytes'] and hashlib.sha256(raw).hexdigest()==CORE['sha256']
 spec=importlib.util.spec_from_file_location('current118_typed_accepted_boundary',CORE['path'])
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def validate_current():
 module=_core();return module.validate_typed(module.ref(BINDING),SELECTION,module.ref(__file__),CORE)
def observe():
 module=_core();return module.observe(module.ref(BINDING),SELECTION,module.ref(__file__),CORE)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
'''.replace('CORE_LITERAL',repr(core)).replace('SELECTION_LITERAL',repr(selection))
    ast.parse(text);observer.write_text(text)
    schema=dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(observer),ledger_key='Root63',expected_status='PASS_Root63_CURRENT118_TYPED_REOBSERVATION_PENDING_ROOT_ACCEPTANCE',current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
    write(root/'OBSERVER-SCHEMA.CURRENT63-CURRENT118.SOURCE-ONLY.json',schema)
    def patch(path,replacements):
        before=path.read_text();after=before
        for left,right in replacements:
            assert left in after,(path,left);after=after.replace(left,right)
        ast.parse(after);path.write_text(after)
        changes.append(dict(path=str(path),previous_SHA256=hashlib.sha256(before.encode()).hexdigest(),successor=ref(path),diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(path)+':retained',tofile=str(path)))))
    importer="""def typed_boundary():
 row=CORE_LITERAL
 assert ref(row['path'])==row
 spec=importlib.util.spec_from_file_location('exact118_typed_boundary_core',row['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
""".replace('CORE_LITERAL',repr(core))
    materializer=cohort/'materialize_admission.py'
    patch(materializer,[('def validate118(b):',importer+'\ndef validate118(b):'),
        (" assert b['nonce_ledger']==baseline['current_ledger'] and b['native_custody_clearance']==baseline['current_free']",' typed_boundary().validate_root_context(b,'+repr(selection)+','+repr(ref(observer))+','+repr(core)+')')])
    capture=cohort/'capture_resources.py'
    old=" source_rows=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in profile['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(profile)]\n assert len(runner.source_directory_postimages(profile))==121"
    overlay=ref(p.S/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json')
    patch(capture,[('def valid_resource_facts(',importer+'\ndef valid_resource_facts('),
                   (old,' source_rows=typed_boundary().source_rows_for_capture(profile,runner,'+repr(overlay)+')')])
    # Actual capture reads its observer from the Root descriptor. Only the exact
    # new source/hash subjects and schema DATA are changed here.
    runtime=cohort/'runtime_guard.py';lines=runtime.read_text().splitlines()
    retained=ast.literal_eval(next(line.split('=',1)[1].strip()for line in lines if line.startswith('RETAINED_SUBJECTS = ')))
    selection_data=json.loads((root/'UPSTREAM-SELECTION.SOURCE-ONLY.json').read_bytes())
    upstream_subjects=json.loads(Path(selection_data['subject_map']['path']).read_bytes())
    retained.update(observer=ref(observer),typed_boundary_core=core,upstream_selection=selection,
                    upstream_post_BFD_observer=selection_data['observer'],upstream_subject_map=selection_data['subject_map'],
                    upstream_inputs=selection_data['inputs'],
                    recursive_current60=upstream_subjects['history:observe_bfd_current60_history.py'],
                    recursive_common=upstream_subjects['history:observe_bfd_root59_history.py'])
    patch(runtime,[(next(line for line in lines if line.startswith('RETAINED_SUBJECTS = ')),'RETAINED_SUBJECTS = '+repr(retained))])
    runtime_ref=ref(runtime)
    for name,prefix,value in [('run_build_only.py','RUNTIME_GUARD_REF=',repr(runtime_ref)),('capture_resources.py','GUARD_SHA=',repr(runtime_ref['sha256']))]:
        path=cohort/name;line=next(x for x in path.read_text().splitlines()if x.startswith(prefix));patch(path,[(line,prefix+value)])
    assembler=cohort/'prepare_publication_rows.py'
    addition="""
# Include every nested runtime DATA dependency, including implicit sibling reads.
core_ref=CORE_LITERAL
assert ref(core_ref['path'])==core_ref
import importlib.util
_spec=importlib.util.spec_from_file_location('exact118_runtime_data_closure',core_ref['path'])
_typed=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_typed)
typed_ref=actual_binding['typed_current_boundary_binding']
selection_ref=SELECTION_LITERAL
aliases_ref=actual_binding['runtime_data_fetched_aliases'];assert ref(aliases_ref['path'])==aliases_ref
aliases=read(aliases_ref['path']);assert aliases['author']=='/root' and aliases['runtime_authority'] is None
add(aliases_ref)
for closure_row in _typed.runtime_data_rows(typed_ref,selection_ref,ref(D/'ROOT-OPERATION-BINDINGS.json')):
 source=closure_row['actual']
 if source['path'] in seen:continue
 if closure_row['requires_explicit_fetched_alias']:
  alias=aliases['aliases'][source['path']]
  actual=ref(repo/alias);assert (actual['bytes'],actual['sha256'])==(source['bytes'],source['sha256'])
  rows.append(dict(actual=source,fetched_equivalent_path=alias));seen.add(source['path'])
 else:add(source)
""".replace('CORE_LITERAL',repr(core)).replace('SELECTION_LITERAL',repr(selection))
    patch(assembler,[('v=dict(scope=z[\'scope\']',addition+'\nv=dict(scope=z[\'scope\']')])
    manifest_path=cohort/'PREPARATION-MANIFEST.json';manifest=json.loads(manifest_path.read_bytes())
    manifest['files']=[ref(x)for x in sorted(cohort.glob('*.py'))]
    manifest['external_inputs']=[row for row in manifest['external_inputs']if row['path']!=str(root/'observe_current61_current118.py')]+[ref(observer),core,selection,ref(root/'OBSERVER-SCHEMA.CURRENT63-CURRENT118.SOURCE-ONLY.json')]
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    # Source/hash DATA templates are refreshed, but no actual Root binding is made.
    def refresh(value):
        if isinstance(value,dict):
            if set(value)=={'path','bytes','sha256'}and str(value['path']).startswith(str(root)+'/')and Path(value['path']).exists():return ref(value['path'])
            return{k:refresh(v)for k,v in value.items()}
        if isinstance(value,list):return[refresh(v)for v in value]
        return value
    for path in cohort.glob('*TEMPLATE*.json'):
        path.write_text(json.dumps(refresh(json.loads(path.read_bytes())),indent=2)+'\n')
    boundary_path=cohort/'ROOT-BOUNDARY.TEMPLATE.NOT-AUTHORITY.json';boundary=json.loads(boundary_path.read_bytes())
    boundary.update(observer=ref(observer),observer_schema=ref(root/'OBSERVER-SCHEMA.CURRENT63-CURRENT118.SOURCE-ONLY.json'),nonce_ledger=None,native_custody_clearance=None)
    boundary_path.write_text(json.dumps(boundary,indent=2)+'\n')
    write(root/'TYPED-CURRENT-BOUNDARY.TEMPLATE.NOT-AUTHORITY.json',dict(schema='mckernel.current118.accepted-post-BFD-boundary.v1',author=None,decision='BIND_CURRENT118_TO_ACCEPTED_POST_BFD_ROOT63',runtime_authority=None,phase='accepted_current',upstream_selection=selection,accepted_current_bindings=None,current_boundary=None,independent_review=None,readonly_release=None))
    write(root/'RUNTIME-DATA-FETCHED-ALIASES.TEMPLATE.NOT-AUTHORITY.json',dict(author=None,runtime_authority=None,aliases={}))
    root_input=root/'ROOT118-INPUT.TEMPLATE.NOT-AUTHORITY.json'
    root_data=json.loads(root_input.read_bytes());root_data.update(nonce_ledger=None,native_custody_clearance=None,current_boundary=None,typed_current_boundary_binding=None,runtime_data_fetched_aliases=None)
    root_input.write_text(json.dumps(root_data,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('next118_exact_source_subjects_only',runtime)
    source_guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(source_guard)
    op_path=cohort/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json';op=json.loads(op_path.read_bytes());op['expected_subjects']=source_guard.subjects();op_path.write_text(json.dumps(op,indent=2)+'\n')
    delta=json.loads((root/'EXACT-SOURCE-DELTAS.RETAINED-RENDERER.json').read_bytes())
    for row in delta['changes']:
        path=Path(row['successor']['path']);row['successor']=ref(path)
        row['diff']=''.join(difflib.unified_diff(Path(row['previous']['path']).read_text().splitlines(True),path.read_text().splitlines(True),fromfile=row['previous']['path'],tofile=str(path)))
    delta['new_typed_sources']=[core,selection,ref(observer)]
    write(root/'EXACT-SOURCE-DELTAS.json',delta)
    write(root/'NEXT-BOUNDARY-SOURCE-DELTAS.json',dict(scope=__doc__.splitlines()[0],retained_renderer=ref(RENDERER),changes=changes,new_observer=ref(observer),new_core=core,selection=selection,runtime_authority=None))
    layout['observer']=observer
    return layout


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);a=p.parse_args()
    print(json.dumps({k:str(v)for k,v in prepare(a.destination).items()}))
