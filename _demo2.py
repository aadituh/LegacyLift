import json
import subprocess

raw = subprocess.check_output(
    [
        "gh",
        "issue",
        "list",
        "--milestone",
        "Demo 2",
        "-s",
        "all",
        "-L",
        "100",
        "--json",
        "number,title,state,assignees,labels",
    ],
    text=True,
)
data = json.loads(raw)
print(f"Demo 2 issues: {len(data)}")
for i in sorted(data, key=lambda x: x["number"]):
    asg = [a["login"] for a in (i.get("assignees") or [])]
    mine = "terrasky064" in asg
    if i["state"] == "OPEN" or mine:
        print(f"#{i['number']} [{i['state']}] {i['title']} | {asg} | mine={mine}")

print("\n--- open PRs by me ---")
raw = subprocess.check_output(
    ["gh", "pr", "list", "-s", "open", "-A", "terrasky064", "--json", "number,title,headRefName"],
    text=True,
)
print(raw)
