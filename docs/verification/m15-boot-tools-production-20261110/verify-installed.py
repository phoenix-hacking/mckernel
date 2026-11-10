from pathlib import Path
import hashlib,json,os,stat
packet=Path(__file__).resolve().parent
output=packet/"output-1"
build=output/"build"
stage=output/"stage"
expected={"prefix":"/usr/local","SBINDIR":"/usr/local/sbin","ETCDIR":"/usr/local/etc","KMODDIR":"/usr/local/kmod","MCKERNELDIR":"/usr/local/smp-x86/kernel","ARCH":"x86_64","BUILDID":"8d288b8","ENABLE_LINUX_WORK_IRQ_FOR_IKC":"ON"}
source=packet/"source/scripts/rust/boot-tools"
text=(source/"config.rs.in").read_text()
for key,value in expected.items():text=text.replace("@"+key+"@",value)
actual=(build/"rust-boot-tools/config.rs").read_text()
assert actual==text,"production generated config differs"
for name in ["platform.rs","reboot.rs","stop.rs","mcreboot_main.rs","mcstop_main.rs"]:
 assert (build/"rust-boot-tools"/name).read_bytes()==(source/name).read_bytes(),name
cache={}
for line in (build/"CMakeCache.txt").read_text().splitlines():
 if line and not line.startswith(("#","//")) and "=" in line:
  key,value=line.split("=",1);cache[key.split(":",1)[0]]=value
assert cache["ENABLE_RUST_BOOT_TOOLS"]=="ON"
assert cache["CMAKE_INSTALL_PREFIX"]=="/usr/local"
assert cache["CMAKE_INSTALL_SBINDIR"]=="sbin"
assert cache["ENABLE_LINUX_WORK_IRQ_FOR_IKC"]=="ON"
expected_relative={"usr/local/sbin/mcreboot.sh","usr/local/sbin/mcstop+release.sh"}
files={p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file() or p.is_symlink()}
assert files==expected_relative,sorted(files)
rows=[]
for name in ["mcreboot.sh","mcstop+release.sh"]:
 original=build/name;installed=stage/"usr/local/sbin"/name
 for p in [original,installed]:
  status=p.lstat();assert stat.S_ISREG(status.st_mode) and not p.is_symlink(),str(p)
  assert status.st_size<67108864
 a=original.read_bytes();b=installed.read_bytes()
 assert a==b,name
 assert a[:6]==b"\x7fELF\x02\x01",name
 assert stat.S_IMODE(installed.stat().st_mode)==0o755,name
 rows.append({"name":name,"built":str(original),"installed":str(installed),"bytes":len(a),"sha256":hashlib.sha256(a).hexdigest(),"mode":"0755","format":"ELF64-little-endian","executed":False})
result={"status":"PASS_EXACT_PRODUCTION_CONFIG_NAMED_ARTIFACT_PRIVATE_INSTALL_BINDING","programs":rows,"generated_config_sha256":hashlib.sha256(actual.encode()).hexdigest(),"source_body_unchanged":True,"default_flip":False,"native_main_or_devices_executed":False,"whole_program_or_original_acceptance":False}
(output/"INSTALL-RESULT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print(json.dumps(result,sort_keys=True))
