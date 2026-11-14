"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Strict structured Docker label-map projection. No query or runtime effects.
"""
import json,re
class Refusal(ValueError):pass
def need(ok,message):
 if not ok:raise Refusal(message)
def strict(raw):
 def pairs(items):
  result={}
  for key,value in items:
   need(key not in result,'duplicate JSON key:'+key);result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Refusal('nonfinite JSON')))
def label_map(value):
 if value is None:return {'kind':'null','value':None}
 need(type(value) is dict and all(type(k) is str and type(v) is str for k,v in value.items()),'Config.Labels must be exact null or full string-to-string map')
 return {'kind':'map','value':dict(value)}
def tagged_label_map(value):
 need(type(value) is dict and set(value)=={'kind','value'},'tagged label kind/value required')
 if value['kind']=='null':need(value['value'] is None,'tagged null exact value')
 elif value['kind']=='map':need(type(value['value']) is dict and all(type(k) is str and type(v) is str for k,v in value['value'].items()),'tagged strict string map')
 else:raise Refusal('unknown label kind')
 return value
def validate_ps_identity(raw,fixed_rows):
 values=[strict(line) for line in raw.splitlines()]
 need(len(values)==len(fixed_rows)==44,'exact44 ps rows')
 fields=('ID','Names','Image','State');expected={row['ID']:{key:row[key] for key in fields} for row in fixed_rows};observed={};display={}
 for value in values:
  need(type(value) is dict and all(key in value and type(value[key]) is str for key in (*fields,'Labels')),'typed ps identity and unmodified Labels display')
  cid=value['ID'];need(cid in expected and cid not in observed,'missing/extra/duplicate ps CID')
  observed[cid]={key:value[key] for key in fields};display[cid]=value['Labels']
 need(observed==expected,'exact historical ps44 CID/name/image/state differs')
 return {'historical_identity_rows':[observed[cid] for cid in sorted(observed)],'unparsed_current_Labels_display':display}
def project(raw,fixed_rows,known_owner_anchors,current_ps_labels):
 values=strict(raw);need(type(values) is list and len(values)==len(fixed_rows)==44,'exact44 inspect objects')
 expected={row['ID']:row for row in fixed_rows};need(len(expected)==44,'unique44 expected CIDs')
 need(type(current_ps_labels) is dict and set(current_ps_labels)==set(expected) and all(type(v) is str for v in current_ps_labels.values()),'exact current ps Labels display CID domain')
 need(type(known_owner_anchors) is dict and set(known_owner_anchors)<=set(expected) and all(type(v) is str for v in known_owner_anchors.values()),'genuine known-owner anchor shape')
 result={}
 for value in values:
  need(type(value) is dict and all(key in value for key in ('Id','Name','Image','Config','State')),'inspect required identity/config/state fields')
  cid=value['Id'];need(type(cid) is str and re.fullmatch('[0-9a-f]{64}',cid) is not None and cid in expected and cid not in result,'unexpected/duplicate CID')
  old=expected[cid];config=value['Config'];state=value['State']
  need(type(value['Name']) is str and value['Name']=='/'+old['Names'],'exact old CID/name')
  need(type(value['Image']) is str and re.fullmatch('sha256:[0-9a-f]{64}',value['Image']) is not None,'typed immutable inspect image ID')
  need(type(config) is dict and 'Image' in config and 'Labels' in config and type(config['Image']) is str,'Config.Image and full labels required')
  labels=label_map(config['Labels'])
  if old['Labels']=='':
   need(current_ps_labels[cid]=='' and (labels['kind']=='null' or labels['value']=={}) and cid not in known_owner_anchors,'historical/current empty display requires exact null or empty map and no owner anchor')
  else:
   need(current_ps_labels[cid]!='' and labels['kind']=='map' and len(labels['value'])>0,'historical/current nonempty display requires nonempty strict map')
  fields={'Status':str,'Running':bool,'Paused':bool,'Restarting':bool,'OOMKilled':bool,'Dead':bool,'Pid':int,'ExitCode':int,'Error':str,'StartedAt':str,'FinishedAt':str}
  need(type(state) is dict and all(key in state and type(state[key]) is cls for key,cls in fields.items()),'typed full State fields')
  need(state['Status']==old['State'] and state['Status'] in ('exited','created','dead') and not state['Running'] and not state['Paused'] and not state['Restarting'] and state['Pid']==0,'exact old stopped state')
  if cid in known_owner_anchors:need(labels['kind']=='map' and labels['value'].get('mckernel.owner')==known_owner_anchors[cid],'genuine owner anchor differs')
  result[cid]={'Id':cid,'Name':value['Name'],'Image':value['Image'],'Config.Image':config['Image'],'Config.Labels':labels,'State':dict(state)}
 need(set(result)==set(expected),'missing/extra CID')
 return [result[cid] for cid in sorted(result)]
def compare(expected,actual):
 keys={'Id','Name','Image','Config.Image','Config.Labels','State'}
 for rows in (expected,actual):
  need(type(rows) is list and len(rows)==44,'exact44 projected rows')
  ids=[]
  for row in rows:
   need(type(row) is dict and set(row)==keys,'exact projected field keys')
   need(all(type(row[key]) is str for key in ('Id','Name','Image','Config.Image')) and type(row['State']) is dict,'typed projected identity/state')
   tagged_label_map(row['Config.Labels']);ids.append(row['Id'])
  need(len(set(ids))==44,'duplicate projected CID')
 left={row['Id']:row for row in expected};right={row['Id']:row for row in actual}
 need(left==right,'full structured projected identities/labels/state differ')
 return True
