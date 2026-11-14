"""Actual parse_env plus a private-ABI C consumer and deterministic allocator seam.

Successful allocation/free/string operations reach genuine HOST libc. Only exact
allocation ordinals return ENOMEM; no resource exhaustion or device/API work.
The predecessor runs solely its defined second-calloc failure path.
"""
from pathlib import Path
import os
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ.get("M15_REPO", Path(__file__).resolve().parents[2]))
HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("M15_PARSE_ENV_SOURCE", ROOT / "ihk/linux/user/rust/whole70/ihklib_environment.rs"))
CONSUMER = Path(os.environ.get("M15_PARSE_ENV_CONSUMER", HERE / "parse_env_consumer.c"))


class M15ParseEnvOwnershipTests(unittest.TestCase):
    def test_exact_parser_has_transactional_ownership(self):
        rustc = os.environ["RUSTC"]
        cc = os.environ.get("CC", "/usr/bin/cc")
        text = SOURCE.read_text()
        function = text[text.index('#[no_mangle]\npub unsafe extern "C" fn parse_env('):text.index("type StringOperation")]
        baseline = os.environ.get("M15_PARSE_ENV_BASELINE_ONLY") == "1"
        root = r'''
use core::ffi::{c_char,c_int,c_void};
extern "C" {
 fn calloc(count:usize,size:usize)->*mut c_void;
 fn strndup(text:*const c_char,length:usize)->*mut c_char;
 fn strdup(text:*const c_char)->*mut c_char;
 fn strsep(cursor:*mut *mut c_char,delimiters:*const c_char)->*mut c_char;
 fn free(pointer:*mut c_void);
 fn __errno_location()->*mut c_int;
 fn run_consumer(baseline:c_int)->c_int;
}
'''
        with tempfile.TemporaryDirectory(prefix="m15-parse-env-", dir=os.environ.get("TMPDIR")) as directory:
            work=Path(directory)
            observer=work/"consumer.o"
            commands=[
                [cc,"-std=gnu11","-Wall","-Wextra","-Werror","-I"+str(ROOT/"ihk/linux/include"),"-c",str(CONSUMER),"-o",str(observer)],
            ]
            unit=work/"parser.rs"
            unit.write_text(root+function+'\nfn main() { unsafe { std::process::exit(run_consumer('+str(int(baseline))+')); } }\n')
            binary=work/"consumer"
            commands.append([rustc,"--edition=2021","-Dwarnings",str(unit),"-o",str(binary),"-C","link-arg="+str(observer),*sum((["-C","link-arg=-Wl,--wrap="+name] for name in ("calloc","strndup","strdup","free")),[])])
            receipt = Path(os.environ["M15_PARSE_ENV_RECEIPT_DIR"]) if os.environ.get("M15_PARSE_ENV_RECEIPT_DIR") else None
            records = []
            if receipt:
                receipt.mkdir(parents=True, exist_ok=False)
            def run(label, command):
                result = subprocess.run(command, capture_output=True, text=True)
                if receipt:
                    (receipt / (label + ".stdout")).write_text(result.stdout)
                    (receipt / (label + ".stderr")).write_text(result.stderr)
                    records.append({"label": label, "argv": command, "returncode": result.returncode})
                    (receipt / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
                    artifacts = {}
                    for artifact in (unit, observer, binary):
                        if artifact.exists():
                            shutil.copyfile(artifact, receipt / artifact.name)
                            artifacts[artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
                    (receipt / "artifacts.json").write_text(json.dumps(artifacts, indent=2) + "\n")
                return result
            for label, command in zip(("cc", "rust"), commands):
                result=run(label, command)
                self.assertEqual(result.returncode,0,"command: "+repr(command)+"\n"+result.stdout+result.stderr)
            result=run("consumer", [str(binary)])
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(result.stdout,"baseline expected-leak observed-live=1 reclaimed=1 restored-live=0 result=-12 outputs-unchanged=1\nbaseline checks=1 failures=0\n" if baseline else "candidate checks=18 failures=0\n")


if __name__ == "__main__":
    unittest.main()
