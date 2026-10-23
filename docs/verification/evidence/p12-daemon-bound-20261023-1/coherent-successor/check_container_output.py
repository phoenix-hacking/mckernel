"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual runner formatting and fixed-source sink inspection; no container/workload.
"""
from pathlib import Path
from unittest.mock import patch
import ast, contextlib, importlib.util, io, json, math, os, resource

D=Path(__file__).resolve().parent;S=D/'source'
assert os.sched_getaffinity(0)=={0}
assert resource.getrlimit(resource.RLIMIT_AS)[0]<=512*2**20
spec=importlib.util.spec_from_file_location('actual_private_runner',S/'native_diagnostic_runner.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
prints=[]
for path in sorted(S.glob('*.py')):
    for node in ast.walk(ast.parse(path.read_bytes(),str(path))):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='print':
            prints.append(dict(source=path.name,line=node.lineno))
assert [x['source'] for x in prints]==['native_diagnostic_runner.py']*2
argv=['--manifest','/fixture/manifest','--attempt-parent','/fixture/p',
      '--attempt-name','attempt-'+'a'*32,'--timeout','7800']
out=io.StringIO();err=io.StringIO();case='P12-fixture-format-only'
with patch.object(r,'run',return_value={'case_id':case}),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
    assert r.main(argv)==0
success=out.getvalue().encode();assert not err.getvalue()
assert json.loads(success)==dict(attempt='attempt-'+'a'*32,case_id=case,status='PROTOCOL_PASS')
failures=[]
for label,char in [('newlines','\n'),('unicode','\U0001f642'),('surrogates','\ud800')]:
    out=io.StringIO();err=io.StringIO()
    exc=Exception(*([char*4096]*4))  # Actual formatter truncates each primitive to2048chars.
    with patch.object(r,'run',side_effect=exc),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        assert r.main(argv)==1
    raw=err.getvalue().encode('utf-8','backslashreplace')
    assert not out.getvalue() and len(err.getvalue())<=4*2048+6+len('native diagnostic failed: ')+1
    failures.append(dict(kind=label,stderr_bytes=len(raw)))
chars=4*2048+6+len('native diagnostic failed: ')+1
input_bytes=6*chars  # Includes surrogate backslash replacement; ordinary UTF8<=4B/char.
records=chars+math.ceil(input_bytes/16384)+1
encoded_upper=6*input_bytes+128*records
assert encoded_upper<2*2**20<16000000
report=dict(scope=__doc__.splitlines()[0],status='PASS_NARROW_ACTUAL_RUNNER_OUTPUT_AND_SINK_INSPECTION',
            explicit_print_sites=prints,success_fixture_bytes=len(success),handled_failures=failures,
            handled_failure_encoded_upper_bytes=encoded_upper,
            max_size16m_bytes=16000000,handled_failure_cannot_rotate_alone=True,
            success_condition='Actual case_id and final manifest not yet bound; fixture is formatting evidence only.',
            remaining_channels=['container Init=True tini output','Python startup/import diagnostics',
                                'uncaught owner.main/_inside setup exceptions and default interpreter traceback',
                                'runner BaseException/write-failure paths outside its except Exception handler'],
            full_container_output_bound_proved=False,physical_allocation_bound_proved=False,
            root=0,docker=0,workloads=0,native_credit=0)
(D/'CONTAINER-OUTPUT-SOURCE-OBSERVATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],handled_failure_encoded_upper_bytes=encoded_upper,
                     full_container_output_bound_proved=False)))
