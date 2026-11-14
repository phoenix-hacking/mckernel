"""Decode one exact v6 resource policy commit from bounded existing host logs.

This is an observation format, not a new ioctl ABI. Public assigned inventory
continues to return EBUSY after shutdown. No Linux page-release or full-cycle
credit follows from the policy table changing ownership.
"""
import re
PREFIX='IHK-SMP: resource-'
NUM=re.compile(r'0|[1-9][0-9]*\Z')
COMMON={'os','generation','epoch','phase'}
HEAD=COMMON|{'rows','emitted','complete'}
CPU=COMMON|{'index','cpu','hardware','numa','state','owner_none','owner_slot','owner_generation'}
MEM=COMMON|{'index','start','bytes','numa','owner_none','owner_slot','owner_generation'}

def evaluate(text, expected_owner, expected_epoch):
    def need(ok, why):
        if not ok: raise ValueError(why)
    need(type(text) is str and len(text.encode()) <= 4*1024*1024,'bounded log')
    need(type(expected_owner) is tuple and len(expected_owner)==2 and
         all(type(v) is int for v in expected_owner) and 0<=expected_owner[0]<64 and
         0<expected_owner[1]<(1<<41) and type(expected_epoch) is int and
         0<expected_epoch<(1<<64),'expected leased owner/epoch')
    blocks=[]
    for line in text.splitlines(keepends=True):
        if PREFIX not in line: continue
        need(line.endswith('\n') and len(line)<=1024,'complete bounded record')
        record=line[line.index(PREFIX):].strip().split(' ')
        kind=record[1][len('resource-'):]
        need(kind in {'cpu-v1','cpu-row-v1','memory-v1','memory-row-v1'},'known record')
        pairs=[item.split('=',1) for item in record[2:]]
        need(all(len(p)==2 for p in pairs),'fields')
        row=dict(pairs);need(len(row)==len(pairs),'duplicate field')
        ishead=kind in {'cpu-v1','memory-v1'}
        need(set(row)==(HEAD if ishead else CPU if kind=='cpu-row-v1' else MEM),'exact fields')
        for key,value in list(row.items()):
            if key in {'phase','state'}:continue
            need(NUM.fullmatch(value) is not None and int(value)<1<<64,'exact u64')
            row[key]=int(value)
        need((row['os'],row['generation'])==expected_owner and row['epoch']==expected_epoch,'exact owner/epoch')
        need(row['phase'] in {'prepared','committed'},'phase')
        if ishead:
            need(row['complete']==1 and row['rows']==row['emitted']<=64,'incomplete inventory is unknown')
            blocks.append((kind.split('-')[0],row,[]))
        else:
            need(bool(blocks) and kind.startswith(blocks[-1][0]+'-') and row['phase']==blocks[-1][1]['phase'],'row block')
            rows=blocks[-1][2];need(row['index']==len(rows)<blocks[-1][1]['emitted'],'ordered unique rows')
            need(row['owner_none'] in (0,1),'known owner disposition')
            if row['owner_none']:
                need(row['owner_slot']==0 and row['owner_generation']==0,'canonical unowned')
            else:need(row['owner_slot']<64 and 0<row['owner_generation']<1<<41,'valid owner')
            rows.append(row)
    need([(k,h['phase']) for k,h,r in blocks]==[
        ('cpu','prepared'),('memory','prepared'),('memory','committed'),('cpu','committed')],'complete coupled commit sequence')
    need(all(h['rows']==len(r) for k,h,r in blocks),'complete row count')
    before_cpu=blocks[0][2];after_cpu=blocks[3][2]
    need(len(before_cpu)>0 and len(before_cpu)==len(after_cpu),'nonempty CPU identity inventory')
    need(len({r['cpu'] for r in before_cpu})==len(before_cpu),'unique CPUs')
    for before,after in zip(before_cpu,after_cpu):
        need(all(before[k]==after[k] for k in ['index','cpu','hardware','numa']),'same CPU identities')
        need(before['state']=='Assigned' and before['owner_none']==0 and
             (before['owner_slot'],before['owner_generation'])==expected_owner,'exact assigned CPU owner')
        need(after['state']=='Online' and after['owner_none']==1,'CPU policy returned online/unowned')
    before_mem=blocks[1][2];after_mem=blocks[2][2]
    def spans(rows):
        out=[]
        for row in rows:
            start,size=row['start'],row['bytes'];end=start+size
            need(size>0 and start%4096==0 and size%4096==0 and end<1<<64 and row['numa']<1<<32,'physical extent geometry')
            need(not out or start>=out[-1][1],'ordered nonoverlapping extents')
            owner=None if row['owner_none'] else (row['owner_slot'],row['owner_generation'])
            out.append((start,end,row['numa'],owner))
        return out
    before=spans(before_mem);after=spans(after_mem)
    owned=[r for r in before if r[3]==expected_owner];need(bool(owned),'nonempty assigned memory identity inventory')
    # Compare exact pointwise extent/NUMA/ownership coverage, allowing canonical
    # adjacent free extents to coalesce at release-all commit.
    def normalized(rows,release):
        result=[]
        for start,end,numa,owner in rows:
            if release and owner==expected_owner:owner=None
            if result and result[-1][1]==start and result[-1][2:]==(numa,owner):
                result[-1]=(result[-1][0],end,numa,owner)
            else:result.append((start,end,numa,owner))
        return result
    need(normalized(before,True)==normalized(after,False),'same physical coverage returned to reserved pool; other owners retained')
    return {'schema':'native-resource-policy-observation-v1','owner':list(expected_owner),
            'boot_epoch':expected_epoch,'cpu_identities':[[r[k] for k in ('cpu','hardware','numa')] for r in before_cpu],
            'returned_memory_extents':[[a,b-a,n] for a,b,n,o in owned],
            'returned_memory_bytes':sum(b-a for a,b,n,o in owned),
            'resource_policy_return_verified':True,'linux_page_release_verified':False,
            'mapping_callback_reference_frame_retirement_verified':False,'complete_cycle_verified':False}
