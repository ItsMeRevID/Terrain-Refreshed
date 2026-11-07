"""Check the mod's data against the vanilla registry of every 1.21.x release.

A datapack fails in two different ways when the running Minecraft is newer than the one it was
written for. The JSON shape can change, which makes the file fail to parse at all, and a
referenced vanilla feature can disappear, which makes the file parse but fail to bind. Both show
up as a registry that never fills, so both have to be checked.
"""

import io
import json
import os
import sys
import urllib.request
import zipfile

VERSIONS = [
    "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6",
    "1.21.7", "1.21.8", "1.21.9", "1.21.10", "1.21.11",
]

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "terrainrefreshed-audit"})
    with urllib.request.urlopen(request) as response:
        return response.read()


def registries(jar):
    result = {}
    with zipfile.ZipFile(io.BytesIO(jar)) as archive:
        for folder in ("placed_feature", "configured_feature", "density_function", "biome"):
            prefix = "data/minecraft/worldgen/%s/" % folder
            result[folder] = sorted(
                name[len(prefix):-len(".json")]
                for name in archive.namelist()
                if name.startswith(prefix) and name.endswith(".json")
            )
        if "pack.mcmeta" in archive.namelist():
            result["pack.mcmeta"] = json.loads(archive.read("pack.mcmeta"))
    return result


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "vanilla-registries"
    os.makedirs(out, exist_ok=True)

    manifest = json.loads(fetch(MANIFEST))
    targets = {e["id"]: e["url"] for e in manifest["versions"] if e["id"] in set(VERSIONS)}

    for version in VERSIONS:
        path = os.path.join(out, version + ".json")
        if os.path.exists(path):
            print("skipping " + version)
            continue

        meta = json.loads(fetch(targets[version]))
        print("downloading " + version + " ...", flush=True)
        jar = fetch(meta["downloads"]["client"]["url"])

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(registries(jar), handle, indent=1, sort_keys=True)
        print("  wrote " + path)

    print("done")


if __name__ == "__main__":
    main()
