"""Source/document consistency only; no product/protocol runtime validation."""
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

def identity(path):
    data = (ROOT / path).read_bytes()
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

def without_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(line.strip() for line in text.splitlines()
                     if line.strip() and not line.lstrip().startswith("//"))

unchanged = []
for path in (
    "experiments/public-api/NativeWeave.Api.Design/Server.cs",
    "experiments/public-api/NativeWeave.Api.Consumers/ServerExamples.cs",
    "experiments/public-api/abi/nativeweave_server_api_v1.h",
):
    baseline = subprocess.check_output(["git", "show", ":" + path], cwd=ROOT).decode()
    current = (ROOT / path).read_text()
    assert without_comments(baseline) == without_comments(current), path
    unchanged.append({**identity(path), "baseline_index_blob": subprocess.check_output(
        ["git", "rev-parse", ":" + path], cwd=ROOT).decode().strip(),
        "only_comments_changed": True})

pattern = re.compile(r"^(?:uint32_t|void)\s+NW_CDECL\s+(nw_server_\w+)\s*\([^;]*\);", re.M)
def prototypes(text):
    return {m.group(1): re.sub(r"\s+", "", m.group(0)) for m in pattern.finditer(text)}
doc = prototypes((ROOT / "docs/api/server.md").read_text())
header = prototypes((ROOT / "experiments/public-api/abi/nativeweave_server_api_v1.h").read_text())
assert doc == header and len(doc) == 48

source = (ROOT / "experiments/public-api/NativeWeave.Api.Design/Server.cs").read_text()
xml_groups = re.findall(r"(?:^[ \t]*///[^\n]*\n)+", source, re.M)
for group in xml_groups:
    ET.fromstring("<root>" + re.sub(r"^[ \t]*///[ ]?", "", group, flags=re.M) + "</root>")

manifest = json.loads((ROOT / "docs/api/server-sources.json").read_text())
source_ids = {entry["id"] for entry in manifest["sources"]}
coverage = json.loads((ROOT / "docs/api/server-coverage.json").read_text())["rows"]
assert len(coverage) == 65
for row in coverage:
    assert all(sid in source_ids for sid in row["source_evidence"]["source_ids"]), row["id"]
policies = json.loads((ROOT / "docs/api/server-symbol-policies.json").read_text())["types"]
subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
result = {
    "scope": "Source/document consistency; no product, native runtime, AOT or HTTP/gRPC/MCP execution",
    "passed": True,
    "declarations": unchanged,
    "c_export_prototypes_equal": 48,
    "csharp_xml_comment_groups_valid": len(xml_groups),
    "coverage_rows_source_ids_valid": len(coverage),
    "type_policy_count": len(policies),
    "git_diff_check_passed": True,
}
(OUT / "consistency-results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
