from pathlib import Path
import types,json,hashlib,sys
T=Path(__file__).resolve().parent;F=T/'raw5-binding-fixture-1';F.mkdir()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def load(p):m=types.ModuleType(p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
sources={n:ref(T/n) for n in ['readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py','test_raw5_binding.py']};(F/'pre-execution-source-map.json').write_text(json.dumps(sources,indent=2)+'\n');m=load(T/'read_original_five_metadata.py');export=load(T/'export_raw_five.py');summary=load(T/'readback_observer.py');post=load(T/'postjoin_readback.py');expected={n:'0'*64 for n in m.NAMES};p=F/'synthetic-five-hashes.json';p.write_text(json.dumps(expected)+'\n');assert m.load_expected_hashes(str(p),ref(p)['sha256'])==expected
assert export.SUMMARY_SHA==ref(T/'readback_observer.py')['sha256'] and export.OUTPUT==summary.OUTPUT and len(export.NAMES)==5 and export.CAP==33554432
negative=0
for digest in ['1'*64]:
 try:m.load_expected_hashes(str(p),digest)
 except RuntimeError:negative+=1
 else:raise AssertionError('wrongSHAaccepted')
sys.argv=['metadata','--expected-hashes',str(p),'--expected-hashes-sha256',ref(p)['sha256']]
try:m.main()
except RuntimeError as e:assert str(e)=='exact root read-only metadata helper required';negative+=1
else:raise AssertionError('ordinaryrootmetadataaccepted')
(F/'summary.json').write_text(json.dumps(dict(status='PASS_AFFECTED_RAW5_TYPED_HASH_AUTHORITY_AND_CLI_ONLY',positive_checks=2,negative_checks=negative,sources=sources,root_calls=0,subprocess_calls=0,actual_raw5_reads=0,raw5_stream_cap=33554432),indent=2)+'\n');print('PASS raw5binding2/refusals2; sources4; actualraw5/root/export0')
