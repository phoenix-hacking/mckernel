from pathlib import Path
import hashlib,json,stat
packet=Path(__file__).resolve().parent
build=packet/"output-1/build"
stage=packet/"output-1/stage"
source=packet/"producer/rust/mcps.rs"
provider=Path("/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/public-abi-join-max-1/consumer-native46d-1/build-output/mcinspect")
expected_source="11bbecd7a0a6f4d098bb737ccca1e64e974e7c91bcc124b989fdc40b552c3b53"
expected_provider="63502c5748397c28ad465a0c0c537cf4480eadbb63be6a40d0a6ca2ff4479dab"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)==expected_source
assert sha(provider)==expected_provider
cache={}
for line in (build/"CMakeCache.txt").read_text().splitlines():
 if line and not line.startswith(("#","//")) and "=" in line:
  key,value=line.split("=",1);cache[key.split(":",1)[0]]=value
for key,value in {"CMAKE_INSTALL_PREFIX":"/usr/local","CMAKE_INSTALL_BINDIR":"bin","CMAKE_INSTALL_LIBDIR":"lib64","CMAKE_BUILD_TYPE":"Debug","ENABLE_RUST_USER_TOOLS":"ON","MCKERNEL_ALLOW_RUNTIME_SCRIPT_FALLBACK":"OFF","MCPS_MATCHED_MCINSPECT":str(provider)}.items():
 assert cache[key]==value,(key,cache.get(key))
rule=(build/"CMakeFiles/mcps_rust_main.dir/build.make").read_text()
assert "MCPS_PREFIX=/usr/local" in rule
assert "MCPS_MCKERNELDIR=/usr/local/smp-x86/kernel" in rule
assert "--crate-name mcps --crate-type lib --edition=2021" in rule
assert "-C panic=abort -C opt-level=2 -C debuginfo=1 -C relocation-model=pic -C force-unwind-tables=no" in rule
link=(build/"CMakeFiles/mcps.dir/link.txt").read_text()
assert "rust/mcps.o" in link and "-fPIE -pie" in link
assert str(provider) not in link,"mcinspect is a subprocess, never a linked Rust/C object"
rows=[]
for name,original in [("mcps",build/"mcps"),("mcinspect",provider)]:
 installed=stage/"usr/local/bin"/name
 for f in [original,installed]:
  st=f.lstat();assert stat.S_ISREG(st.st_mode) and not f.is_symlink()
 assert original.read_bytes()==installed.read_bytes()
 assert stat.S_IMODE(installed.stat().st_mode)==0o755
 assert installed.read_bytes()[:6]==b"\x7fELF\x02\x01"
 rows.append({"name":name,"built_or_reused":str(original),"installed":str(installed),"bytes":installed.stat().st_size,"sha256":sha(installed),"mode":"0755","executed":False})
actual_mcps=(build/"mcps").read_bytes()
for value in [b"/usr/local/bin/mcinspect\0",b"--kernel=/usr/local/smp-x86/kernel/mckernel.img\0",b"--ps\0"]:
 assert value in actual_mcps,"actual configured argument bytes missing"
# Byte presence only corroborates exact source/env/command/object/link readback;
# it is not a complete behavior, ABI, native or selected-default acceptance.
files={f.relative_to(stage).as_posix() for f in stage.rglob("*") if f.is_file() or f.is_symlink()}
assert files=={"usr/local/bin/mcps","usr/local/bin/mcinspect"}
result={"status":"PASS_ACTUAL_PRODUCTION_CONFIG_MCPS_PRIVATE_INSTALL_AND_MATCHING_REUSED_MCINSPECT","programs":rows,"source_sha256":sha(source),"MCPS_PREFIX":"/usr/local","MCPS_MCKERNELDIR":"/usr/local/smp-x86/kernel","actual_configured_argument_bytes_present":True,"artifact_commands_and_ELF_import_RPATH_still_require_result_join":True,"old_cases_rerun":False,"mcps_or_mcinspect_main_executed":False,"native_or_original_acceptance":False}
(packet/"output-1/INSTALL-RESULT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print(json.dumps(result,sort_keys=True))
