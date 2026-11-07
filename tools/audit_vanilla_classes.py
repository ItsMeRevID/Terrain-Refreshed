"""Check that the classes the mod mixes into and calls still exist in every 1.21.x release.

A mod is compiled against one Minecraft version but the loader remaps it for whichever version
is running, so a class that was renamed or removed breaks the mod at load time on the newer
version even though nothing in the mod changed.
"""

import json
import os
import sys
import urllib.request

VERSIONS = [
    "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6",
    "1.21.7", "1.21.8", "1.21.9", "1.21.10", "1.21.11",
]

WANTED = [
    "net.minecraft.world.level.biome.MultiNoiseBiomeSourceParameterList",
    "net.minecraft.world.level.biome.MultiNoiseBiomeSourceParameterList$Preset",
    "net.minecraft.world.level.biome.Climate",
    "net.minecraft.world.level.biome.Climate$Parameter",
    "net.minecraft.world.level.biome.Climate$ParameterList",
    "net.minecraft.world.level.biome.Climate$ParameterPoint",
    "net.minecraft.world.level.biome.Climate$TargetPoint",
    "net.minecraft.world.level.biome.Biome",
    "net.minecraft.world.level.levelgen.feature.Feature",
    "net.minecraft.world.level.levelgen.feature.PlacedFeature",
    "net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration",
    "net.minecraft.world.level.levelgen.VerticalAnchor",
    "net.minecraft.world.level.levelgen.placement.PlacementUtils",
    "net.minecraft.world.level.levelgen.WorldGenLevel",
    "net.minecraft.world.level.levelgen.Heightmap",
    "net.minecraft.core.registries.Registries",
    "net.minecraft.core.HolderGetter",
    "net.minecraft.core.Holder",
    "net.minecraft.resources.ResourceKey",
]

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "terrainrefreshed-audit"})
    with urllib.request.urlopen(request) as response:
        return response.read()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "vanilla-mappings"
    os.makedirs(out, exist_ok=True)

    manifest = json.loads(fetch(MANIFEST))
    targets = {e["id"]: e["url"] for e in manifest["versions"] if e["id"] in set(VERSIONS)}

    for version in VERSIONS:
        path = os.path.join(out, version + ".txt")
        if not os.path.exists(path):
            meta = json.loads(fetch(targets[version]))
            print("downloading mappings " + version + " ...", flush=True)
            with open(path, "wb") as handle:
                handle.write(fetch(meta["downloads"]["client_mappings"]["url"]))

        names = set()
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if "->" not in line:
                    continue
                left = line.split("->")[0].strip()
                if left.endswith(":"):
                    left = left[:-1]
                names.add(left)

        missing = [w for w in WANTED if w not in names]
        print("%-8s missing: %s" % (version, missing if missing else "none"))


if __name__ == "__main__":
    main()
