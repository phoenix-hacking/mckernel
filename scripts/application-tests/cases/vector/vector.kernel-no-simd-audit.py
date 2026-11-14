#!/usr/bin/env python3
import json, re, sys

FORBIDDEN = re.compile(r'(?i)\b(v?movdqu|vadd|vmul|vfm|ymm|zmm|xmm|aes|pclmul|sha|gf2p8|vpdp|vpermb)')

def audit(records):
    findings = []
    for rec in records:
        text = rec.get("disassembly", "")
        hits = sorted(set(m.group(0).lower() for m in FORBIDDEN.finditer(text)))
        findings.append({"artifact": rec.get("artifact"), "forbidden_simd_tokens": hits, "status": "FAIL" if hits else "PASS"})
    return findings

def main():
    data = json.load(sys.stdin)
    findings = audit(data.get("artifacts", []))
    print(json.dumps({"artifacts": findings, "all_clean": all(x["status"] == "PASS" for x in findings)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
