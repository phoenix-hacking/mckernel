import hashlib, json, struct, subprocess, types
from pathlib import Path
HERE=Path(__file__).resolve().parent
module=types.ModuleType("corrected_driver")
exec(compile((HERE/"compile_phase4_driver.py").read_bytes(),str(HERE/"compile_phase4_driver.py"),"exec"),module.__dict__)
original=HERE.parent/"work/output/build/current-guest-control-fullcrate-1/native-mckernel_rust.o"
data=original.read_bytes()
class Saved:
    def __init__(self,name,data):self.name,self.data=name,data
    def read_bytes(self):return self.data
    def __str__(self):return str(original)+" [saved validator selection "+self.name+"]"
positive=module.object_info(Saved("native-mckernel_rust.o",data))
header=struct.unpack_from("<16sHHIQQQIHHHHHH",data)
sections=[struct.unpack_from("<IIQQQQIIQQ",data,header[6]+i*64) for i in range(header[12])]
positions={}
for section in sections:
    if section[1]!=2:continue
    strings=sections[section[6]];table=data[strings[4]:strings[4]+strings[5]]
    for pos in range(section[4],section[4]+section[5],24):
        name,info,other,index,value,size=struct.unpack_from("<IBBHQQ",data,pos)
        end=table.find(b"\0",name)
        if info>>4 in (1,2):positions[table[name:end].decode("ascii")]=pos
def refused(label,name,payload):
    try:module.object_info(Saved(name,payload))
    except AssertionError:return {"case":label,"refused":True}
    raise AssertionError("negative accepted: "+label)
negatives=[]
changed=bytearray(data);struct.pack_into("<H",changed,positions["release_cpuid"]+6,0)
negatives.append(refused("release_cpuid undefined", "native-mckernel_rust.o",changed))
changed=bytearray(data);struct.pack_into("<H",changed,positions["clone_thread"]+6,1);changed[positions["clone_thread"]+4]=18
negatives.append(refused("clone_thread wrongly defined", "native-mckernel_rust.o",changed))
negatives.append(refused("Rust object cannot stand in for C provider", "constructor-process.o",data))
# Duplicate a real global symbol row under the release_cpuid string-table name.
changed=bytearray(data);target=positions["process_fork_construct_current_v1"];release=positions["release_cpuid"]
changed[target:target+24]=data[release:release+24]
negatives.append(refused("duplicate release_cpuid provider", "native-mckernel_rust.o",changed))
proc=subprocess.run(["/usr/bin/nm","-g",str(original)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
assert not proc.stderr
witnesses={name:[line for line in proc.stdout.decode().splitlines() if line.split()[-1:]==[name]] for name in ("release_cpuid","clone_thread")}
assert len(witnesses["release_cpuid"])==1 and witnesses["release_cpuid"][0].split()[-2]=="T"
assert len(witnesses["clone_thread"])==1 and witnesses["clone_thread"][0].split()[-2]=="U"
result={"status":"PASS","actual_saved_object":positive,"nm_witnesses":witnesses,"negative_controls":negatives,"compiler_executed":False,"source_mutation":False,"linked_artifact_acceptance":False}
with (HERE/"saved-object-validator-result.json").open("x") as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write("\n")
print(json.dumps({"status":"PASS","negative_controls":len(negatives),"witnesses":witnesses,"object_sha256":positive["sha256"]},sort_keys=True))
