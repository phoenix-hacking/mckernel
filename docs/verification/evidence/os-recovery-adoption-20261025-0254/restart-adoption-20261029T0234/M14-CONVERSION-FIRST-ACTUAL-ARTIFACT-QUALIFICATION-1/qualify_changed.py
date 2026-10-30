"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact selected changed providers, source ABI, imports and final consumers.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('context.py').read_text(),str(Path(__file__).with_name('context.py')),'exec'))
base=read(A/'M14-CURRENT119-ACTUAL-ARTIFACT-QUALIFICATION-1/independent-review-1/INDEPENDENT-ACTUAL-CURRENT119-ARTIFACT-ACCEPTANCE.json')
baserust=elf(auth(base['tuple']['Rust']));basekc=elf(auth(base['tuple']['generic_C']));baseimg=Final(auth(base['tuple']['image']))
scan=read(D/'CHANGE-SCAN.ACTUAL.json');failures=[];provider_proofs=[];consumer_proofs=[]
for n in scan['Rust_new']:
 try:
  s=own(new,n);f=image.sym(n);assert(s['type'],s['bind'],s['size'])==(f['type'],f['bind'],f['size'])and(s['type'],s['bind'])==(2,1)
  assert not[(r['link_token'],q)for r,e in objects if e is not new for q in defined(e,n)]
  q,raw,tokens,records=relocated_function(new,n,image)
  provider_proofs.append(dict(name=n,input=s,final=f,relocations=records,all_final_bytes=True,unique_Rust_owner=True))
 except Exception as exc:failures.append(dict(group='changed_provider',name=n,error=repr(exc)))
# Positive external consumers in actual current input objects, not only a symbol presence check.
for n in scan['Rust_new']:
 edges=[]
 for row,e in objects:
  for s in e.symbols:
   if s['shndx'] and s['size'] and s['type'] in (1,2):
    for rel in rels(e,s):
     if rel['target']['name']==n:
      try:
       _,raw,tokens,records=relocated_function(e,s['name'],image)
       edges.append(dict(object=row['link_token'],consumer=s['name'],type=s['type'],size=s['size'],target=n,offset=rel['offset'],full_final_bytes=True))
      except Exception as exc:failures.append(dict(group='external_consumer',provider=n,consumer=s['name'],error=repr(exc)))
 if not edges:failures.append(dict(group='no_relocation_consumer',name=n))
 consumer_proofs.append(dict(provider=n,edges=edges))
# Changed inherited functions caused by removing local callback bodies/using explicit Rust forwarders.
changed=[x for x in scan['Rust_changed']if isinstance(x,str)]
changed_proofs=[]
for n in changed:
 try:
  s,raw,tokens,records=relocated_function(new,n,image);changed_proofs.append(dict(name=n,input=s,final=image.sym(n),relocations=records,all_final_bytes=True))
 except Exception as exc:failures.append(dict(group='changed_inherited_consumer',name=n,error=repr(exc)))
# Every remaining generic function is a current external consumer of this changed crate.
c_proofs=[]
for n in sorted(allocated(kc,2)):
 try:
  s,raw,tokens,records=relocated_function(kc,n,image);c_proofs.append(dict(name=n,input=s,final=image.sym(n),relocations=records,all_final_bytes=True))
 except Exception as exc:failures.append(dict(group='remaining_C_consumer',name=n,error=repr(exc)))
# Global import delta relative to actual119, exact unique provider + symbol type/size in actual link.
imports=lambda e:{s['name']for s in e.symbols if not s['shndx']and s['bind']==1}
import_proofs=[]
for n in sorted(imports(new)-imports(baserust)):
 owners=[(r['link_token'],q)for r,e in objects for q in defined(e,n)];assert len(owners)==1,(n,owners)
 s=owners[0][1];f=image.sym(n);assert(s['type'],s['bind'],s['size'])==(f['type'],f['bind'],f['size'])
 import_proofs.append(dict(name=n,owner=owners[0][0],input=s,final=f))
result=dict(scope=__doc__.splitlines()[0],provider_proofs=provider_proofs,external_current_consumer_proofs=consumer_proofs,changed_inherited_consumer_proofs=changed_proofs,remaining_C_consumer_proofs=c_proofs,failures=failures,new_Rust_imports=import_proofs,removed_Rust_imports=sorted(imports(baserust)-imports(new)),native_acceptance=False,C_retirement=False)
(D/'CHANGED-PROVIDERS-AND-CONSUMERS.ACTUAL.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(providers=len(provider_proofs),external_provider_groups=len(consumer_proofs),changed_inherited=len(changed_proofs),remaining_C=len(c_proofs),new_imports=import_proofs,failures=failures)))
