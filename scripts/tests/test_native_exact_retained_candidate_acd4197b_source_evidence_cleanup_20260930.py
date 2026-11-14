import importlib.util,json
from pathlib import Path
import pytest
SRC=Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-acd4197b-source-evidence-cleanup-20260930.py";s=importlib.util.spec_from_file_location("acd",SRC);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def ok():return {"lsof":{"returncode":1,"output":"","stderr":""},"mount":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n"},"docker":{"returncode":0,"output":json.dumps({"ID":m.CONTAINER_ID[:12],"Names":m.CONTAINER_NAME,"State":"exited"})},"retained_inspect":{"returncode":0,"output":json.dumps({"Status":"exited","Pid":0,"ExitCode":1,"OOMKilled":False}),"stderr":""}}
def test_commit():assert m.COMMIT.startswith("acd4197b")
def test_identity():assert m.ID=="1831:4063240"
def test_root():assert "scratch-11" in str(m.ROOT)
def test_empty_lsof():m.validate(ok())
@pytest.mark.parametrize("k",["lsof","mount","docker","retained_inspect"])
def test_census_errors(k):
 c=ok();c[k]["returncode"]=2
 with pytest.raises(SystemExit):m.validate(c)
def test_lsof_reference():
 c=ok();c["lsof"]["output"]="COMMAND PID\nx 1\n"
 with pytest.raises(SystemExit):m.validate(c)
def test_lsof_warning():
 c=ok();c["lsof"]["stderr"]="warning"
 with pytest.raises(SystemExit):m.validate(c)
def test_nested_mount():
 c=ok();c["mount"]["output"]+="/dev/x ext4 1:2 /nested\n"
 with pytest.raises(SystemExit):m.validate(c)
def test_running_container():
 c=ok();c["docker"]["output"]+="\n"+json.dumps({"State":"running","Names":"mckernel-exact-11"})
 with pytest.raises(SystemExit):m.validate(c)
def test_malformed_docker():
 c=ok();c["docker"]["output"]="not-json\n"
 with pytest.raises(SystemExit):m.validate(c)
def test_retained_container_required_and_terminal():
 c=ok();c["docker"]["output"]=""
 with pytest.raises(SystemExit):m.validate(c)
 for key,value in (("Status","running"),("Pid",1),("ExitCode",0),("OOMKilled",True)):
  c=ok();state=json.loads(c["retained_inspect"]["output"]);state[key]=value;c["retained_inspect"]["output"]=json.dumps(state)
  with pytest.raises(SystemExit):m.validate(c)
def test_bad_plan():
 with pytest.raises(SystemExit):m.apply({"schema":"bad","status":"AUDIT_PASS"})
def test_protected_failure():assert "additive-parameter-failure" in str(m.FAILURE)
def test_protected_exportset():assert "exportset-15" in str(m.EXCLUSION)
def test_nested_delta():assert "nested_delta_preserved" in SRC.read_text()
def test_no_container_remove():assert "docker rm" not in SRC.read_text()
def test_nlink_filter():assert "st.st_nlink!=1" in SRC.read_text()
def test_symlink_filter():assert "p.is_symlink()" in SRC.read_text()
def test_fsync():assert "os.fsync" in SRC.read_text()
def test_apply_split():assert "--apply" in SRC.read_text()
def test_protected_paths():assert "protected_paths" in SRC.read_text()
def test_target_hash():assert "sha(p.read_bytes())" in SRC.read_text()
def test_mount_pin():assert "/dev/loop39" in SRC.read_text()
def test_plan_schema():assert "exact-git-source-cleanup.v1" in SRC.read_text()
def test_durable_write_no_replace(tmp_path):
 p=tmp_path/"plan.json";m.write(p,{"a":1})
 with pytest.raises(SystemExit):m.write(p,{"a":2})
