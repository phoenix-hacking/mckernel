"""Call the genuine private owner request consumer, with no owner.run effects."""
from pathlib import Path
import hashlib,json,sys,types
P=Path(__file__).resolve().parent
assert len(sys.argv)==3,'exact reviewed delta path and SHA required'
delta_path=Path(sys.argv[1]);data=delta_path.read_bytes();assert hashlib.sha256(data).hexdigest()==sys.argv[2];delta=json.loads(data)
row=delta['owner_source'];path=Path(row['path']);blob=path.read_bytes();assert hashlib.sha256(blob).hexdigest()==row['sha256']
module=types.ModuleType('exact_remaining_image_owner');module.__file__=str(path);exec(compile(blob,str(path),'exec'),module.__dict__)
receipt_path=P/'remaining-attempt-1/serialization-receipt.json';receipt=json.loads(receipt_path.read_text());r=receipt['request'];request=Path(r['path']);request_bytes=request.read_bytes();assert hashlib.sha256(request_bytes).hexdigest()==r['sha256'];q=json.loads(request_bytes)
bound=module._validate_request(q)
assert not any(bound['work'].iterdir()) and not any(bound['owner_evidence'].iterdir())
assert str(bound['work'])==delta['overrides']['work_root'] and q['remaining_image_seed']==delta['overrides']['remaining_image_seed']
result={'status':'PASS_GENUINE_SERIALIZED_REMAINING_OWNER_REQUEST','request':r,'owner_source':row,'source_derivative_sha256':q['source_derivative_sha256'],'materialization_sha256':q['materialization_sha256'],'empty_fresh_work':True,'seed_manifest':q['remaining_image_seed']['manifest'],'no_owner_run':True,'actual_seed':False,'compiler':False,'root_or_Docker':False}
with (P/'remaining-attempt-1/actual-owner-request-consumer.json').open('x') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps({'status':result['status'],'request_sha256':r['sha256'],'actual_seed':False,'root_or_Docker':False}))
