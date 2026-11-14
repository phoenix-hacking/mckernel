"""No-effect actual helper normalization fixture; metadata only, no source copies."""
from pathlib import Path
import json,types,tempfile
N=Path(__file__).resolve().parent
helper=types.ModuleType('actual_materializer_fixture');helper.__file__=str(N/'materialize_sources.py')
exec(compile(Path(helper.__file__).read_bytes(),helper.__file__,'exec'),helper.__dict__)
plan=json.loads((N/'source-manifest.json').read_bytes());assert len(plan['rows'])==159
before=(N/'materialized-source').exists();assert not before
paths=helper.normalized_relatives(plan['rows']);assert len(paths)==len(set(paths))==159
assert helper.normalized_relatives([{'relative':'kernel/../executer/include/uti.h'}])==[Path('executer/include/uti.h')]
assert helper.normalized_relatives([{'relative':'kernel/./rust//lib.rs'}])==[Path('kernel/rust/lib.rs')]
negatives=[[{'relative':'../escape'}],[{'relative':'kernel/../../escape'}],[{'relative':'/absolute'}],[{'relative':'.'}],[{'relative':'kernel/../executer/include/uti.h'},{'relative':'executer/include/uti.h'}]]
for rows in negatives:
    try:helper.normalized_relatives(rows)
    except AssertionError:pass
    else:raise AssertionError('unsafe path or collision accepted')
with tempfile.TemporaryDirectory(prefix='normalizer-metadata-',dir=N) as tmp:
    p=Path(tmp)/'normalized-paths.json';p.write_text(json.dumps([x.as_posix() for x in paths]));assert len(json.loads(p.read_bytes()))==159
assert not (N/'materialized-source').exists() and not (N/'work').exists()
print(json.dumps({'status':'PASS_NO_EFFECT_ACTUAL_HELPER_NORMALIZATION','actual_rows':159,'additional_positive_vectors':2,'negative_vectors':len(negatives),'source_copies':0,'compilers':0,'materialized':False}))
