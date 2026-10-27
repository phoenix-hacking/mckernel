# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,datetime,subprocess,os,time,re
p=Path(__file__).resolve().parent
planfile=p/"EXACT-BOUNDED-PLAN.json"
plan=json.loads(planfile.read_text())
assert not (p/"ACTUAL-COMMAND-RESULTS.json").exists()
for group in ["inputs","headers","tools"]:
 for path,entry in plan[group].items():
  f=Path(path);assert f.stat().st_size==entry["bytes"] and hashlib.sha256(f.read_bytes()).hexdigest()==entry["sha256"],path
result={"scope":plan["scope"],"plan_sha256":hashlib.sha256(planfile.read_bytes()).hexdigest(),"limits":plan["limits"],"cwd":str(p),"environment":{"uname":list(os.uname()),**{k:os.environ.get(k) for k in ["PATH","LD_LIBRARY_PATH","LIBRARY_PATH","CPATH","C_INCLUDE_PATH","RUSTFLAGS","RUSTC_WRAPPER"]}},"start_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"commands":[],"status":"RUNNING"}
for cmd in plan["commands"]:
 label=cmd["label"];entry={**cmd,"start_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()};start=time.monotonic()
 with (p/(label+".stdout")).open("xb") as out,(p/(label+".stderr")).open("xb") as err:
  child=subprocess.Popen(cmd["wrapped_argv"],cwd=cmd["cwd"],stdout=out,stderr=err,start_new_session=True)
  entry["pid"]=child.pid;entry["returncode"]=child.wait();entry["direct_child_joined"]=True
 entry["streams_closed"]=True
 try:os.killpg(child.pid,0);entry["process_group_absent"]=False
 except ProcessLookupError:entry["process_group_absent"]=True
 entry["wall_seconds_observed"]=time.monotonic()-start;entry["finish_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for stream in ["stdout","stderr","time"]:
  f=p/(label+"."+stream);entry[stream]={"path":str(f),"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()}
 timing=(p/(label+".time")).read_text()
 entry["CPU_user_seconds"]=float(re.search(r"User time \(seconds\): ([0-9.]+)",timing).group(1))
 entry["CPU_system_seconds"]=float(re.search(r"System time \(seconds\): ([0-9.]+)",timing).group(1))
 entry["max_RSS_KiB"]=int(re.search(r"Maximum resident set size \(kbytes\): (\d+)",timing).group(1))
 result["commands"].append(entry)
 if entry["returncode"]!=0 or not entry["process_group_absent"]:
  result["status"]="STOPPED_FIRST_UNEXPECTED_FAILURE";break
 (p/"ACTUAL-COMMAND-RESULTS.json").write_text(json.dumps(result,indent=2)+"\n")
else:result["status"]="PASS_HOST_SLICE_READY_FOR_REVIEW_NOT_DEFAULT_NOT_NATIVE"
result["finish_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
result["CPU_seconds_total"]=sum(c["CPU_user_seconds"]+c["CPU_system_seconds"] for c in result["commands"])
result["wall_seconds_commands_total"]=sum(c["wall_seconds_observed"] for c in result["commands"])
result["largest_command_RSS_KiB"]=max(c["max_RSS_KiB"] for c in result["commands"])
(p/"ACTUAL-COMMAND-RESULTS.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k not in ["commands","environment"]},indent=2))
print("commands",[(c["label"],c["returncode"]) for c in result["commands"]])
