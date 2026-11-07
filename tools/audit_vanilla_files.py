"""Extract the vanilla worldgen files that the mod's own files have to match.

Only a handful of vanilla files matter: the tree features, because they show the block state
and feature configuration shape of the running version, and the noise and density files, because
the mod overrides the overworld density graph.
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


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "vanilla-files"
    os.makedirs(out, exist_ok=True)

    manifest = json.loads(fetch(MANIFEST))
    targets = {e["id"]: e["url"] for e in manifest["versions"] if e["id"] in set(VERSIONS)}

    for version in VERSIONS:
        version_dir = os.path.join(out, version)
        if os.path.exists(os.path.join(version_dir, ".done")):
            print("skipping " + version)
            continue
        os.makedirs(version_dir, exist_ok=True)

        meta = json.loads(fetch(targets[version]))
        print("downloading " + version + " ...", flush=True)
        jar = fetch(meta["downloads"]["client"]["url"])

        with zipfile.ZipFile(io.BytesIO(jar)) as archive:
            names = archive.namelist()
            keep = [
                n for n in names
                if n.startswith("data/minecraft/worldgen/configured_feature/tree/")
                or n.startswith("data/minecraft/worldgen/placed_feature/tree/")
                or n.startswith("data/minecraft/worldgen/noise/")
                or n.startswith("data/minecraft/worldgen/density_function/overworld/")
                or n.startswith("data/minecraft/worldgen/biome/")
                or n in ("pack.mcmeta", "data/minecraft/worldgen/noise_settings/overworld.json")
            ]
            for name in keep:
                target = os.path.join(version_dir, name.replace("/", "__"))
                with open(target, "wb") as handle:
                    handle.write(archive.read(name))

            print("  kept %d files" % len(keep))

        open(os.path.join(version_dir, ".done"), "w").close()

    print("done")


if __name__ == "__main__":
    main()
