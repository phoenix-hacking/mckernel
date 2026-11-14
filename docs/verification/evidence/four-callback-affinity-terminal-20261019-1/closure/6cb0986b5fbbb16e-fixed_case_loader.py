"""Fixed fresh8b field specializations; frozen algorithms are never copied."""
from pathlib import Path
import hashlib,json
CONTEXT = {'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/fixed-case-specializations.json', 'sha256': '401c638d9a5a55ecd607522f9d756acda1ac84ca777fcda5603ebe1f5bce2b66', 'bytes': 10197}
def checked(ref):
 raw=Path(ref['path']).read_bytes()
 assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'fixed specialization source pin'
 return raw
def bind_source_root(source):
 x=json.loads(checked(CONTEXT));old="NAMESPACE / 'materialized-source' if key == 'source_root'"
 assert source.count(old)==1,'exact inherited source-root boundary'
 return source.replace(old,"Path("+repr(x['source_root'])+") if key == 'source_root'",1)
def apply(namespace,name):
 context=json.loads(checked(CONTEXT));spec=context['specs'][name];source=checked(spec['source']).decode()
 for edit in spec['edits']:
  assert source.count(edit['old'])==edit['count'],'fixed field occurrence '+name
  source=source.replace(edit['old'],edit['new'])
 namespace['_bind_source_root']=bind_source_root
 saved=namespace['__name__'];namespace['__name__']='_fresh8b_frozen_'+name.replace('.','_')
 try:exec(compile(source,namespace['__file__'],'exec'),namespace)
 finally:namespace['__name__']=saved
