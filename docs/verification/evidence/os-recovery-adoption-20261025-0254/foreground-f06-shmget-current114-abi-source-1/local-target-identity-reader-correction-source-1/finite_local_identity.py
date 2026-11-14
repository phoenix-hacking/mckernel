"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite expert-bound 15 object pairs/19 reference positions; no counter/name waiver.
"""
import copy,hashlib

def expected_snapshot(row,side):
 return dict(symbol=row[side+'_symbol'],section=row['section_semantics'],section_file_offset=row[side+'_section_file_offset'],initial_hex=row['initial_hex'],fields=row.get('descriptor_fields',[]))

def check_snapshot(actual,row,side):
 expected=expected_snapshot(row,side)
 assert actual==expected,('finite local object identity differs',row['kind'],side,actual,expected)
 assert actual['symbol']['bind']==0 and actual['symbol']['type']==1
 assert hashlib.sha256(bytes.fromhex(actual['initial_hex'])).hexdigest()==row['initial_sha256']
 assert actual['symbol']['value']==row['storage_relative_offset']
 return (row['kind'],row['old_symbol']['name'],row['new_symbol']['name'])

def edge_key(edge,side):
 return (edge['function'],edge['offset'],edge['type'],edge['addend'],edge[side+'_target'])

def mapped_edge(edges,pairs,side,function,offset,reltype,addend,target):
 key=(function,offset,reltype,addend,target)
 hits=[e for e in edges if edge_key(e,side)==key]
 assert len(hits)==1,('unlisted local reference position',side,key)
 edge=hits[0];rows=[p for p in pairs if p['old_symbol']['name']==edge['old_target'] and p['new_symbol']['name']==edge['new_target']]
 assert len(rows)==1
 return rows[0]

def synthetic_controls(proof):
 pairs=proof['finite_local_target_pairs'];edges=proof['mismatched_relocations'];rejected=[]
 def reject(label,call):
  try:call()
  except AssertionError:rejected.append(label);return
  raise AssertionError(('negative control accepted',label))
 # Complete storage/symbol/section identity, not coincidentally equal initial data.
 for row in pairs:
  for side in ['old','new']:check_snapshot(expected_snapshot(row,side),row,side)
 row=pairs[0];snap=expected_snapshot(row,'old')
 mutations=[('LOCALbinding',lambda x:x['symbol'].__setitem__('bind',1)),('OBJECTtype',lambda x:x['symbol'].__setitem__('type',2)),('sectionname',lambda x:x['section'].__setitem__('name','.data')),('sectionflags',lambda x:x['section'].__setitem__('flags',2)),('sectiontype',lambda x:x['section'].__setitem__('type',8)),('sectionsize',lambda x:x['section'].__setitem__('size',x['section']['size']+1)),('alignment',lambda x:x['section'].__setitem__('align',1)),('objectsize',lambda x:x['symbol'].__setitem__('size',31)),('relativevalue',lambda x:x['symbol'].__setitem__('value',8))]
 for label,mut in mutations:
  x=copy.deepcopy(snap);mut(x);reject(label,lambda x=x:check_snapshot(x,row,'old'))
 for byte,label in [(0,'filepointer'),(8,'funcpointer'),(16,'fmtNULL'),(24,'line'),(27,'flags'),(28,'padding')]:
  x=copy.deepcopy(snap);z=bytearray.fromhex(x['initial_hex']);z[byte]^=1;x['initial_hex']=z.hex();reject(label,lambda x=x:check_snapshot(x,row,'old'))
 for field,key,value in [(0,'cstring','wrong/origin'),(1,'cstring','wrong_function'),(0,'type',2),(1,'addend',513),(0,'offset',1),(0,'target_section','.data'),(1,'target_point',0)]:
  x=copy.deepcopy(snap);x['fields'][field][key]=value;reject('descriptor_'+str(field)+'_'+key,lambda x=x:check_snapshot(x,row,'old'))
 for side in ['old','new']:
  for e in edges:mapped_edge(edges,pairs,side,e['function'],e['offset'],e['type'],e['addend'],e[side+'_target'])
 e=edges[0]
 for label,args in [('unlisted_function',('wrong',e['offset'],e['type'],e['addend'],e['old_target'])),('unlisted_offset',(e['function'],e['offset']+1,e['type'],e['addend'],e['old_target'])),('unlisted_type',(e['function'],e['offset'],1,e['addend'],e['old_target'])),('unlisted_addend',(e['function'],e['offset'],e['type'],1,e['old_target'])),('unlisted_target',(e['function'],e['offset'],e['type'],e['addend'],'ddebug.unlisted'))]:reject(label,lambda args=args:mapped_edge(edges,pairs,'old',*args))
 private=[p for p in pairs if p['kind']=='source_private_mutable_static'];assert len(private)==2
 edge=private[0]['references'][0]
 reject('redirect_privatePID_to_logcounter',lambda:mapped_edge(edges,pairs,'old',edge['function'],edge['offset'],edge['type'],edge['addend'],private[1]['old_symbol']['name']))
 return dict(status='PASS_SYNTHETIC_METADATA_ONLY',negative_controls=rejected,positive_pairs=15,positive_edges=19,artifact_or_provider_execution=False)

def validate_actual_pairs(proof,base,candidate,own,rels,data,descriptor,cstring,allocated):
 pairs=proof['finite_local_target_pairs'];edges=proof['mismatched_relocations']
 assert len(pairs)==15 and len(edges)==19
 results=[]
 for side,e in [('old',base),('new',candidate)]:
  for row in pairs:
   symbol=own(e,row[side+'_symbol']['name']);sec=e.sections[symbol['shndx']]
   assert len([s for s in e.symbols if s['type']==1 and s['shndx']==symbol['shndx'] and s['value']==symbol['value']])==1,('duplicate aliased storage',symbol)
   fields=[];internal=rels(e,symbol)
   if row['kind']=='genuine_ddebug_descriptor':
    descriptor(e,symbol,row['filename'],row['function'],row['line'])
    for r in internal:
     target=r['target'];target_section=e.sections[target['shndx']];assert target_section['flags']&2 and not target_section['flags']&5
     fields.append(dict(addend=r['addend'],cstring=cstring(e,r),offset=r['offset'],target_point=target['value']+r['addend'],target_section=target_section['name'],target_type=target['type'],type=r['type']))
   else:
    assert not internal
    if row['kind']=='exact_function_name_literal':assert sec['flags']==2 and data(e,symbol)==row['literal'].encode()+b'\0'
    else:assert row['kind']=='source_private_mutable_static' and row['source_function']=='do_signal'
   actual=dict(symbol=symbol,section={k:sec[k] for k in ['align','flags','name','size','type']},section_file_offset=sec['offset'],initial_hex=data(e,symbol).hex(),fields=sorted(fields,key=lambda x:x['offset']))
   check_snapshot(actual,row,side)
   positions=[]
   for name,body in allocated(e).items():
    for r in rels(e,body):
     if r['target']['index']==symbol['index']:positions.append((name,r['offset'],r['type'],r['addend'],symbol['name']))
   expected=[edge_key(x,side) for x in row['references']]
   assert sorted(positions)==sorted(expected),('all private reference positions',symbol['name'],positions,expected)
   results.append(dict(side=side,name=symbol['name'],kind=row['kind'],all_reference_positions=positions,full_storage_and_source_identity=True))
 return results
