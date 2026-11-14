"""Independent stopped-rescue oracle; source/mock validation only."""
import hashlib, json, os, stat
from pathlib import Path
EXPECTED = {"control": {"status": "COMPLETED", "raw_wait": 0}, "stopped-rescue": {"status": "RESCUED", "raw_wait": 256, "stop": 4991, "fixture_wait": [9, 9], "adoption": "ECHILD"}}
def digest(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)
def read(path):
    path=Path(path); require(path.is_absolute() and path.resolve(strict=True)==path, "canonical artifact")
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd); require(stat.S_ISREG(info.st_mode) and info.st_size<=16*1024**2,"bounded artifact")
        raw=os.read(fd,info.st_size+1); require(len(raw)==info.st_size,"complete artifact"); return raw
    finally: os.close(fd)
def strict(path): return json.loads(read(path), object_pairs_hook=lambda pairs: {k:v for k,v in pairs})
def validate_retained(root,case):
    require(case in EXPECTED,"unknown case"); record=strict(Path(root)/"rescue-report.json"); expected=EXPECTED[case]
    require(record.get("application_acceptance") is False and record.get("backend_enabled") is False,"acceptance boundary")
    require(record.get("status")==expected["status"] and record.get("raw_collector_wait")==expected["raw_wait"],"collector wait")
    if case=="stopped-rescue":
        require(record.get("raw_stop_status")==4991 and record.get("raw_fixture_waits")==[9,9],"raw rescue waits")
        require(record.get("adoption_observed")=="ECHILD" and record.get("ready")==["READY","STOP_ARMED"],"rescue transitions")
    return record
