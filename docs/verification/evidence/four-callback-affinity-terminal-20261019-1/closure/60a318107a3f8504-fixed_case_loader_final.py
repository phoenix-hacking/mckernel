"""Fixed fresh8b field specializations; frozen algorithms are never copied."""
from pathlib import Path
import hashlib,json
CONTEXT = {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/fixed-case-specializations-final.json', 'sha256': '9b4e24920480fd47fa2e30bb0cf66dbbe38451e02ed98b64c3420cd5f7422602', 'bytes': 11911}
def checked(ref):
 raw=Path(ref['path']).read_bytes()
 assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'fixed specialization source pin'
 return raw
def bind_source_root(source):
 x=json.loads(checked(CONTEXT));old="NAMESPACE / 'materialized-source' if key == 'source_root'"
 assert source.count(old)==1,'exact inherited source-root boundary'
 return source.replace(old,"Path("+repr(x['source_root'])+") if key == 'source_root'",1)
def bind_observer_sources(source):
 import types
 x=json.loads(checked(CONTEXT));ref=x['producer_layout'];m=types.ModuleType('_fresh8b_protected_request_layout');m.__file__=ref['path'];exec(compile(checked(ref),m.__file__,'exec'),m.__dict__)
 request=json.loads(m.checked(x['request']))
 expected={'gitlink-inputs.json':request['gitlink_manifest'],'image-toolchain.json':request['toolchain_manifest'],'materialization-receipt.json':x['materialization_receipt']['path'],'thin-inputs.json':request['source_manifest']}
 assert x['manifest_paths']==expected,'actual request metadata source paths'
 old=x['observer_source_statement'];assert source.count(old)==1,'one inherited selected-source statement'
 new='selected_paths.update((FULL_SOURCE_MAP_PATH,'+','.join('Path('+repr(expected[name])+')' for name in ('gitlink-inputs.json','image-toolchain.json','materialization-receipt.json','thin-inputs.json'))+'))'
 return source.replace(old,new,1)
def apply(namespace,name):
 context=json.loads(checked(CONTEXT));spec=context['specs'][name];source=checked(spec['source']).decode()
 for edit in spec['edits']:
  assert source.count(edit['old'])==edit['count'],'fixed field occurrence '+name
  source=source.replace(edit['old'],edit['new'])
 namespace['_bind_source_root']=bind_source_root
 namespace['_bind_observer_sources']=bind_observer_sources
 saved=namespace['__name__'];namespace['__name__']='_fresh8b_frozen_'+name.replace('.','_')
 try:exec(compile(source,namespace['__file__'],'exec'),namespace)
 finally:namespace['__name__']=saved
