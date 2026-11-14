import hashlib,json,struct,types
from pathlib import Path
N=Path(__file__).resolve().parent;B=N.parent
m=types.ModuleType("corrected_saved_artifact_oracle");m.__file__=str(N/"corrected_saved_artifact_oracle.py");exec(compile(Path(m.__file__).read_bytes(),m.__file__,"exec"),m.__dict__)
r=json.loads((B/"request.json").read_bytes());work=Path(r["work_root"]);src=Path(r["mounts"][0]["source"]);out=work/"output/build/real-mcexec-1";commands=json.loads(Path(r["commands"]["path"]).read_bytes())
assert len(commands)==6
statuses=[]
for command in commands:
 d=json.loads((out/command["selection"]/"status.json").read_bytes());assert d["argv"]==command["argv"] and d["cwd"]==command["cwd"] and d["exit_code"]==0 and d["direct_wait"] and d["owned_process_group_absent"];statuses.append({"selection":command["selection"],"exit_code":0,"direct_wait":True,"group_absent":True})
artifacts=[m.object_info(work/relative)for relative in m.ARTIFACTS]
dependencies={}
for role,name in[("C","actual-C-dependencies.json"),("link","actual-link-dependencies.json")]:
 d=json.loads((out/name).read_bytes());depfile=work/Path(d["path"]).relative_to("/work");assert depfile.stat().st_size==d["bytes"] and m.sha(depfile)==d["sha256"]
 assert d["complete_actual_rule_captured"] and not d["historical_dependency_proof_claimed"]
 for row in d["actual_dependencies"]:
  p=Path(row["path"])
  if Path("/src")in p.parents:actual=src/p.relative_to("/src")
  elif Path("/work/output/build")in p.parents:actual=work/p.relative_to("/work")
  else:
   assert any(m.under(p,root)for root in m.IMAGE_DEPENDENCY_ROOTS);assert row["authority"]=="exact pinned readonly image or readonly accepted nightly root";continue
  assert actual.is_file()and not actual.is_symlink()and actual.stat().st_size==row["bytes"]and m.sha(actual)==row["sha256"]
 dependencies[role]={"depfile":str(depfile),"sha256":d["sha256"],"bytes":d["bytes"],"actual_dependencies":len(d["actual_dependencies"]),"source_generated_bytes_rechecked":True,"immutable_image_descriptors_reused_from_pinned_executed_driver":True}
# Meaningful actual-ELF mutations isolate missing selected entry and duplicate provider.
p=work/m.ARTIFACTS[1];data=p.read_bytes();h=struct.unpack_from("<16sHHIQQQIHHHHHH",data);sections=[struct.unpack_from("<IIQQQQIIQQ",data,h[6]+i*64)for i in range(h[12])];positions={}
for section in sections:
 if section[1]!=2:continue
 strings=sections[section[6]];table=data[strings[4]:strings[4]+strings[5]]
 for pos in range(section[4],section[4]+section[5],24):
  name,info,other,index,value,size=struct.unpack_from("<IBBHQQ",data,pos);end=table.find(b"\0",name)
  if info>>4 in(1,2):positions[table[name:end].decode("ascii")]=(pos,index,info&15)
class Saved:
 name="mcexec_helpers.o"
 def __init__(self,data):self.data=data
 def read_bytes(self):return self.data
 def __str__(self):return"negative saved ELF view"
def refuse(label,payload):
 try:m.object_info(Saved(payload))
 except AssertionError:return {"case":label,"refused":True}
 raise AssertionError("negative accepted: "+label)
entry="mcexec_main_loop_thread_func_body";changed=bytearray(data);struct.pack_into("<H",changed,positions[entry][0]+6,0);negatives=[refuse("selected Rust entry undefined",changed)]
constrained=set().union(*(a|b for a,b in m.RULES.values()))|m.ASM_SYMBOLS|{"act_clone_start"};spare=next(v[0]for name,v in positions.items()if name not in constrained and v[1]and v[2]==2);changed=bytearray(data);pos=positions[entry][0];changed[spare:spare+24]=data[pos:pos+24];negatives.append(refuse("duplicate selected Rust entry preserving all constrained symbols",changed))
result={"status":"SAVED_REAL_MCEXEC_ALL6_AND5_ARTIFACTS_VALIDATION_PASS","original_case_status_unmodified":"FAIL postcompile inventory only","actual_producer_statuses":statuses,"artifacts":artifacts,"actual_generated_dependencies":dependencies,"negative_controls":negatives,"actual_link_previously_performed":True,"compiler_Docker_root_or_ownership_executed_by_validator":False,"runtime_install_native_default_ACK_acceptance":False}
with(N/"saved-artifact-validation-result.json").open("x")as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write("\n")
print(json.dumps({"status":result["status"],"actual_producers":6,"artifacts":5,"negatives":len(negatives),"final_mcexec_sha256":artifacts[-1]["sha256"]},sort_keys=True))
