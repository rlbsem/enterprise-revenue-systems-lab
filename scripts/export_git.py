"""Export a reviewed Git tree for connector-based checkpoint publication."""
import argparse
import base64
import json
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--binary")
p.add_argument("--offset", type=int, default=0)
p.add_argument("--batch", type=int, default=-1)
p.add_argument("--text")
p.add_argument("--since")
a = p.parse_args()
if a.text:
    data = subprocess.check_output(["git", "show", "HEAD:" + a.text]).decode("utf-8")
    print(json.dumps(data[a.offset:a.offset+10000]))
elif a.binary:
    data = subprocess.check_output(["git", "show", "HEAD:" + a.binary])
    print(base64.b64encode(data).decode()[a.offset:a.offset+10000])
else:
    files = subprocess.check_output(["git", "diff", "--name-only", a.since, "HEAD"] if a.since else ["git", "ls-files"], text=True).splitlines()
    entries, binaries = [], []
    for name in files:
        data = subprocess.check_output(["git", "show", "HEAD:" + name])
        if name.endswith((".zip", ".png")):
            binaries.append({"path": name, "encoded_length": len(base64.b64encode(data))})
        else:
            entries.append({"path": name, "mode": "100644", "type": "blob", "content": data.decode("utf-8")})
    print(json.dumps({"entries": entries[a.batch:a.batch+5] if a.batch >= 0 else [],
                      "files": [{"path": e["path"], "length": len(e["content"])} for e in entries],
                      "count": len(entries), "binaries": binaries}))
