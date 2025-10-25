import glob
import os
import sys
import json

if len(sys.argv) != 2:
    print("Usage: python create_delta_jsonl.py <sde-compare-folder>")
    sys.exit(1)

sde_compare_folder = sys.argv[1]
os.makedirs("delta", exist_ok=True)

with open("jsonl/build-number.txt", "r") as f:
    build_number = f.read().strip()
with open(f"{sde_compare_folder}/build-number.txt", "r") as f:
    build_number_previous = f.read().strip()
with open("delta/build-number.delta.txt", "w") as f:
    f.write(f"{build_number_previous} -> {build_number}")

stats = {
    "build-number": {
        "previous": build_number_previous,
        "current": build_number,
    },
    "files": {},
}

def load_jsonl(filename):
    """Load JSONL file and return as dictionary"""
    data = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    data[record["id"]] = record["data"]
    return data

for filename in glob.glob("jsonl/*.jsonl"):
    filename = filename.split("/")[-1]
    print(f"Creating delta for {filename} ...")

    # It might be that the official SDE doesn't have all the files.
    if os.path.exists(f"{sde_compare_folder}/{filename}"):
        left = load_jsonl(f"{sde_compare_folder}/{filename}")
    else:
        left = {}

    right = load_jsonl(f"jsonl/{filename}")

    keys = set(left.keys()) | set(right.keys())
    delta = {"added": {}, "removed": {}, "changed": {}}
    for key in keys:
        if key not in left:
            delta["added"][key] = right[key]
        elif key not in right:
            delta["removed"][key] = {}
        elif left[key] != right[key]:
            # The official SDE has some quirks, which makes change-detection hard.
            # Fix up a bunch to make the diff significant smaller.

            # sofFactionName / sofMaterialSetID / masteries / traits is not in the EVE client data, but is in the official SDE.
            if filename == "types.jsonl":
                if "sofFactionName" in left[key]:
                    del left[key]["sofFactionName"]
                if "sofMaterialSetID" in left[key]:
                    del left[key]["sofMaterialSetID"]
                if "masteries" in left[key]:
                    del left[key]["masteries"]
                if "traits" in left[key]:
                    del left[key]["traits"]

            # Sometimes the "obsolete" field exists, but it is always False.
            if filename == "iconIDs.jsonl" and "obsolete" in left[key]:
                del left[key]["obsolete"]

            # displayWhenZero is also added in the official SDE when it is false; sometimes. Not always.
            if (
                filename == "dogmaAttributes.jsonl"
                and "displayWhenZero" in left[key]
                and left[key]["displayWhenZero"] == False
            ):
                del left[key]["displayWhenZero"]

            # IconIDs and GraphicIDs description field are not in the EVE client data, but are in the official SDE.
            if (
                filename in ("iconIDs.jsonl", "graphicIDs.jsonl")
                and "description" in left[key]
                and "description" not in right[key]
            ):
                del left[key]["description"]

            # Sometimes the "descriptionID" is deleted when there are no strings, and sometimes an empty "en" is left behind.
            if "descriptionID" in left[key] and left[key]["descriptionID"]["en"] == "":
                del left[key]["descriptionID"]

            # Compare again, after possibly fixing up the data.
            if left[key] == right[key]:
                continue

            delta["changed"][key] = right[key]

    if delta["added"] or delta["removed"] or delta["changed"]:
        stats["files"][filename] = {
            "added": len(delta["added"]),
            "removed": len(delta["removed"]),
            "changed": len(delta["changed"]),
        }

        filename = filename.replace(".jsonl", ".delta.jsonl")
        with open(f"delta/{filename}", "w", encoding="utf-8") as f:
            # Write delta as JSONL
            for key, value in delta["added"].items():
                f.write(json.dumps({"id": key, "action": "added", "data": value}, ensure_ascii=False) + '\n')
            for key, value in delta["removed"].items():
                f.write(json.dumps({"id": key, "action": "removed", "data": value}, ensure_ascii=False) + '\n')
            for key, value in delta["changed"].items():
                f.write(json.dumps({"id": key, "action": "changed", "data": value}, ensure_ascii=False) + '\n')


summary = ""
for filename, file_stats in sorted(stats["files"].items()):
    summary += f"- `{filename}`: "

    schange = []
    if file_stats["added"]:
        schange.append(f"{file_stats['added']} added")
    if file_stats["removed"]:
        schange.append(f"{file_stats['removed']} removed")
    if file_stats["changed"]:
        schange.append(f"{file_stats['changed']} changed")

    summary += ", ".join(schange) + "\n"

with open("delta/files.delta.md", "w") as f:
    f.write(summary)
