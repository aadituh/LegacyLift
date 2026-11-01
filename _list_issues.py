import json
import subprocess
import sys

raw = subprocess.check_output(
    ["gh", "issue", "list", "-s", "open", "-L", "100", "--json", "number,title,assignees,milestone,labels,body"],
    text=True,
)
data = json.loads(raw)
for i in data:
    asg = [a["login"] for a in (i.get("assignees") or [])]
    if "terrasky064" not in asg:
        continue
    m = (i.get("milestone") or {}).get("title")
    labels = [l["name"] for l in (i.get("labels") or [])]
    print(f"#{i['number']}: {i['title']}")
    print(f"  milestone={m} labels={labels}")
    print("---BODY---")
    print(i.get("body") or "")
    print("===END===\n")
