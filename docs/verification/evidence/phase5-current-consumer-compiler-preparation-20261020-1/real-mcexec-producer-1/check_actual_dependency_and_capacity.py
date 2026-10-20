import hashlib,json,resource,tempfile,types
from pathlib import Path
N=Path(__file__).resolve().parent
def load(filename):
 m=types.ModuleType(filename);m.__file__=str(N/filename);exec(compile((N/filename).read_bytes(),m.__file__,"exec"),m.__dict__);return m
driver=load("compile_real_mcexec_driver.py");owner=load("current_mcexec_owner.py")
assert resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20)
request=json.loads((N/"request.json").read_bytes());snapshot=owner.capacity_snapshot(request,"/home/holden")
assert snapshot["budgets"]=={"host":1610612736,"scratch":771751936}
with tempfile.TemporaryDirectory(prefix="dependency-fixture-",dir=N)as temporary:
 root=Path(temporary);src=root/"src";build=root/"build";image=root/"image";outside=root/"outside"
 for path in(src,build,image,outside):path.mkdir()
 (src/"known.h").write_bytes(b"actual-helper-fixture\n");(build/"fresh.o").write_bytes(b"generated");(image/"header.h").write_bytes(b"image");(outside/"unapproved.h").write_bytes(b"outside")
 pin={"relative":"known.h","bytes":(src/"known.h").stat().st_size,"sha256":hashlib.sha256((src/"known.h").read_bytes()).hexdigest()}
 manifest={"rows":[pin]};dep=build/"actual.d"
 def call(text):
  dep.write_text(text);return driver.dependency_info(dep,build,manifest,str(src),str(build),(str(image),))
 positive=call("fixture.o: "+str(src/"known.h")+" "+str(build/"fresh.o")+" "+str(image/"header.h")+"\n")
 assert len(positive["actual_dependencies"])==3
 refused=[]
 def negative(label,text):
  try:call(text)
  except(AssertionError,FileNotFoundError):refused.append(label);return
  raise AssertionError("negative accepted: "+label)
 negative("outside approved roots","fixture.o: "+str(outside/"unapproved.h")+"\n")
 (src/"unfrozen.h").write_bytes(b"unfrozen");negative("unfrozen source dependency","fixture.o: "+str(src/"unfrozen.h")+"\n")
 (src/"escape.h").symlink_to(outside/"unapproved.h");negative("source symlink escape","fixture.o: "+str(src/"escape.h")+"\n")
 negative("make expansion refusal","fixture.o: $(UNBOUND)\n")
result={"status":"PASS","actual_capacity_snapshot":snapshot,"dependency_positive":positive,"negative_refusals":refused,"Docker_compiler_ownership_executed":False}
with(N/"dependency-and-capacity-helper-result.json").open("x")as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write("\n")
print(json.dumps({"status":"PASS","negative_refusals":len(refused),"source_count":20,"host_growth_bytes":1610612736},sort_keys=True))
