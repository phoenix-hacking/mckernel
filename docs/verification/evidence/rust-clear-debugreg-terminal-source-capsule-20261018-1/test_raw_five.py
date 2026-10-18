import copy,importlib.util,io,json,tarfile
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('c',P/'consume_raw_five.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
obs=dict(selected_files=[],inventories={'root':[]},client_ledger=[],mount={},root_lock={},target={},request_lease_absent=True)
values={'observer-result.json':dict(status='PASS_READ_ONLY_OBSERVATION_ONLY'),'observation.json':obs,'cleanup-release-draft.json':dict(status='NOT_RELEASED',observation=obs),'new-object-metadata.json':dict(objects=[]),'ownership.json':dict(nonce='fixture')}
data={n:c.canon(values[n]) for n in c.NAMES}
d=dict(file_sha256={n:c.sha(b) for n,b in data.items()},result=values['observer-result.json'],new_object_metadata=values['new-object-metadata.json'],ownership=values['ownership.json'],cleanup_draft=dict(status='NOT_RELEASED',observation_canonical_sha256=c.sha(c.canon(obs))),observation=dict(obs,inventories={'root':dict(entries=0,canonical_sha256=c.sha(c.canon([])))}))
def archive(names=None,bad=None):
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as t:
  for n in names or c.NAMES:
   raw=data[n];i=tarfile.TarInfo(n);i.size=len(raw);i.mode=0o600
   if bad:bad(i)
   t.addfile(i,io.BytesIO(raw))
 return buf.getvalue()
c.validate(archive(),d);refused=0
for raw,draft in [(archive(list(reversed(c.NAMES))),d),(archive(list(c.NAMES)+[c.NAMES[0]]),d),(archive(bad=lambda i:setattr(i,'uid',1000)),d),(archive(bad=lambda i:setattr(i,'mode',0o644)),d)]:
 try:c.validate(raw,draft)
 except AssertionError:refused+=1
 else:raise AssertionError('bad member binding accepted')
bad=copy.deepcopy(d);bad['file_sha256'][c.NAMES[0]]='0'*64
try:c.validate(archive(),bad)
except AssertionError:refused+=1
else:raise AssertionError('bad digest accepted')
bad=copy.deepcopy(d);bad['cleanup_draft']['observation_canonical_sha256']='0'*64
try:c.validate(archive(),bad)
except AssertionError:refused+=1
else:raise AssertionError('bad observation binding accepted')
print(json.dumps(dict(status='PASS_RAW_FIVE_CONSUMER_FIXTURES',positive=1,refusals=refused,root_execution=False)))
