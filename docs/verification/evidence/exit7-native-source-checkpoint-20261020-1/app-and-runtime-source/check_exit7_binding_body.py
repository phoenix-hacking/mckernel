"""Proposed no-process actual-body checks; outputs stdout only, never runtime."""
from pathlib import Path
import ast,copy,importlib.util,json
D=Path(__file__).resolve().parent
cfg=json.loads((D/'INPUT-AND-DECLARED-DATA.json').read_bytes())
old=ast.parse(Path(cfg['tested_runtime_evaluator']['path']).read_text())
new=ast.parse((D/'native_diagnostic.py').read_text())
# Sole semantic AST change must be the exact immutable case-data assignment.
def without_binding(tree):
    return ast.dump(ast.Module(body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M03_CASE_BINDING' for t in n.targets))],type_ignores=[]),include_attributes=False)
assert without_binding(old)==without_binding(new)
spec=importlib.util.spec_from_file_location('exit7_body',D/'native_diagnostic.py')
nd=importlib.util.module_from_spec(spec);spec.loader.exec_module(nd)
b=nd.M03_CASE_BINDING
m=dict(case_id=b['case_id'],payload=copy.deepcopy(b['payload']),
       artifacts=dict(copy.deepcopy(b['matched_artifacts']),payload=b['payload_artifact'],initramfs=b['accepted_stage_base'],root_base=b['accepted_stage_base']),
       modules=copy.deepcopy(b['matched_modules']),profile=copy.deepcopy(b['matched_profile']),
       staging=dict(base_initramfs=b['accepted_stage_base']))
nd._validate_m03_binding(m)
mutations=[('case_id',),('payload','oracle','exit_code'),('payload','oracle','stdout_hex'),('payload','oracle','stderr_hex'),('payload','argv'),('artifacts','payload'),('artifacts','mckernel_image'),('artifacts','mcexec'),('modules',),('profile',),('artifacts','initramfs'),('artifacts','root_base'),('staging','base_initramfs')]
for path in mutations:
    candidate=copy.deepcopy(m);cursor=candidate
    for key in path[:-1]:cursor=cursor[key]
    cursor[path[-1]]=None
    try:nd._validate_m03_binding(candidate)
    except nd.DiagnosticError:pass
    else:raise AssertionError('accepted mutation '+repr(path))
assert b['payload']['oracle']['exit_code']==7
assert bytes.fromhex(b['payload']['oracle']['stdout_hex'])==Path(cfg['expected_stdout']['path']).read_bytes()
assert bytes.fromhex(b['payload']['oracle']['stderr_hex'])==Path(cfg['expected_stderr']['path']).read_bytes()
print(json.dumps(dict(status='PASS_EXACT_BINDING_BODY_ONLY',accepted=1,rejected=len(mutations),unchanged_all_function_AST=True,guest_runs=0)))
