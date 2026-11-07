"""Pull the vanilla worldgen JSON for every 1.21.x release straight from Mojang.

The mod ships a datapack, and a datapack is rejected outright when the JSON schema of the
running Minecraft no longer matches it. Comparing the vanilla files of every release is the
only reliable way to see where the schema moved, because the changes are silent and each
one produces its own set of "Failed to parse" lines at registry load.

The vanilla worldgen data lives in the client jar, not the server jar: the server jar is a
bundler that only ships the game classes.
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

WANTED = [
    "pack.mcmeta",
    "data/minecraft/worldgen/biome/plains.json",
    "data/minecraft/worldgen/biome/desert.json",
    "data/minecraft/worldgen/density_function/overworld/sloped_cheese.json",
    "data/minecraft/worldgen/noise_settings/overworld.json",
    "data/minecraft/worldgen/biome_source/multi_noise.json",
    "data/minecraft/worldgen/placed_feature/tree/oak.json",
    "data/minecraft/worldgen/configured_feature/tree/oak.json",
    "data/minecraft/worldgen/placed_feature/vegetation/flower_default.json",
    "data/minecraft/worldgen/configured_feature/vegetation/flower_default.json",
    "data/minecraft/worldgen/configured_feature/tree/azalea.json",
    "data/minecraft/worldgen/placed_feature/tree/azalea.json",
    "data/minecraft/worldgen/density_function/overworld/vegetation.json",
    "data/minecraft/worldgen/density_function/overworld/shifted_density.json",
    "data/minecraft/worldgen/world_preset/overworld.json",
]

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "terrainrefreshed-audit"})
    with urllib.request.urlopen(request) as response:
        return response.read()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "vanilla"
    os.makedirs(out, exist_ok=True)

    manifest = json.loads(fetch(MANIFEST))
    targets = {e["id"]: e["url"] for e in manifest["versions"] if e["id"] in set(VERSIONS)}

    for version in VERSIONS:
        url = targets.get(version)
        if not url:
            print("version not in the manifest: " + version)
            continue

        meta = json.loads(fetch(url))
        print("downloading " + version + " ...", flush=True)
        jar = fetch(meta["downloads"]["client"]["url"])

        version_dir = os.path.join(out, version)
        os.makedirs(version_dir, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(jar)) as archive:
            names = set(archive.namelist())
            for wanted_name in WANTED:
                if wanted_name not in names:
                    continue
                target = os.path.join(version_dir, wanted_name.replace("/", "__"))
                with open(target, "wb") as handle:
                    handle.write(archive.read(wanted_name))

            worldgen = [n for n in names if n.startswith("data/minecraft/worldgen/")]
            print("  %s: %d worldgen files" % (version, len(worldgen)))

    print("done")


if __name__ == "__main__":
    main()
