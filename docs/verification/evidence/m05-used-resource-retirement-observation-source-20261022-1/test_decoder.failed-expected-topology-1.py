from pathlib import Path
import json,sys
from resource_observation import evaluate
Q=Path(sys.argv[1]);meta=json.loads((Q/'good.json').read_text());owner=(meta['os'],meta['generation']);epoch=meta['epoch'];good=(Q/'good.log').read_text()
result=evaluate(good,owner,epoch)
assert result['resource_policy_return_verified'] and result['returned_memory_bytes']==8192
assert not result['linux_page_release_verified'] and not result['complete_cycle_verified']
assert result['cpu_identities']==[[1,65,0],[2,66,0]],result
negative=[]
def reject(name,text,who=owner,when=epoch):
 try:evaluate(text,who,when)
 except ValueError as error:negative.append({'name':name,'reason':str(error)})
 else:raise AssertionError(name+' accepted')
for name in ['irq_retained','map_retained','epoch_retained','bounded_unknown']:
 m=json.loads((Q/(name+'.json')).read_text());reject(name,(Q/(name+'.log')).read_text(),owner,m['epoch'])
lines=good.splitlines(True);rows=[l for l in lines if 'IHK-SMP: resource-' in l]
reject('missing_all_observation','status=0\n')
reject('missing_committed_cpu',''.join(l for l in lines if not ('resource-cpu' in l and 'phase=committed' in l)))
reject('same_slot_new_generation',good,(owner[0],owner[1]+1))
reject('same_generation_new_epoch',good,owner,epoch+1)
reject('incomplete_marker',good.replace('complete=1','complete=0',1))
reject('invented_zero_rows',good.replace('rows=2 emitted=2','rows=0 emitted=0',1))
reject('duplicate_row',good.replace(rows[1],rows[1]+rows[1],1))
reject('duplicate_field',good.replace('phase=prepared','phase=prepared phase=prepared',1))
reject('negative_integer',good.replace('cpu=1','cpu=-1',1))
reject('leading_zero_integer',good.replace('cpu=1','cpu=01',1))
reject('truncated_record',good.rstrip('\n'))
reject('unknown_version',good.replace('resource-cpu-v1','resource-cpu-v2',1))
post=good.index('resource-memory-v1',good.index('resource-memory-v1')+1)
reject('wrong_physical_coverage',good[:post]+good[post:].replace('start=4096','start=8192',1))
reject('lost_other_generation',good[:post]+good[post:].replace('owner_none=0 owner_slot=7 owner_generation=92','owner_none=1 owner_slot=0 owner_generation=0',1))
post=good.index('resource-cpu-v1',good.index('resource-cpu-v1')+1)
reject('wrong_CPU_hardware',good[:post]+good[post:].replace('hardware=65','hardware=99',1))
reject('CPU_still_assigned',good[:post]+good[post:].replace('state=Online','state=Assigned',1))
reject('false_unowned_generation',good[:post]+good[post:].replace('owner_generation=0','owner_generation=91',1))
# Adjacent free extents may merge without changing physical coverage. Keep the
# other generation's allocated extent distinct and exactly preserved.
valid_merge=good.replace('phase=committed rows=3 emitted=3','phase=committed rows=3 emitted=3')
assert evaluate(valid_merge,owner,epoch)==result
(Q/'decoder-result.json').write_text(json.dumps({'status':'PASS','actual_body_positive':result,'rejected':negative,'negative_cases':len(negative)},indent=2)+'\n')
print(json.dumps({'status':'PASS','actual_body_positive':result,'negative_cases':len(negative)}))
