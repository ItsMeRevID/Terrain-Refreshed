"""Reproduce the game's feature-order cycle check over every biome.

The game chains the placed features of each biome into one long list and then looks for cycles.
Two biomes that share features in a different order create a cycle, so the generator has to emit
step lists whose relative order agrees with vanilla.
"""

import json
import os
import sys
import zipfile

MC_JAR = "C:/Users/advan/.gradle/caches/fabric-loom/26.3/minecraft-common.jar"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VANILLA = os.path.join(ROOT, "build", "vanilla-biomes")
MOD = os.path.join(ROOT, "src", "main", "resources", "data", "terrainrefreshed", "worldgen", "biome")


def vanilla_biomes():
    if os.path.isdir(VANILLA):
        return {
            name[:-5]: json.load(open(os.path.join(VANILLA, name)))
            for name in os.listdir(VANILLA)
            if name.endswith(".json")
        }

    os.makedirs(VANILLA, exist_ok=True)
    out = {}
    with zipfile.ZipFile(MC_JAR) as z:
        for entry in z.namelist():
            if entry.startswith("data/minecraft/worldgen/biome/") and entry.endswith(".json"):
                name = entry.rsplit("/", 1)[1]
                path = os.path.join(VANILLA, name)
                with open(path, "wb") as fh:
                    fh.write(z.read(entry))
                out[name[:-5]] = json.loads(z.read(entry))
    return out


def mod_biomes():
    return {
        name[:-5]: json.load(open(os.path.join(MOD, name)))
        for name in os.listdir(MOD)
        if name.endswith(".json")
    }


def chain(biome):
    flat = []
    for step_index, step in enumerate(biome["features"]):
        for feature in step:
            flat.append((feature, step_index))
    return flat


def edges_for(biomes):
    edges = {}
    for name, biome in biomes.items():
        flat = chain(biome)
        for i in range(len(flat) - 1):
            edges.setdefault(flat[i], set()).add(flat[i + 1])
    return edges


def find_cycle(edges):
    colour = {}
    stack = []

    def visit(node):
        colour[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            state = colour.get(nxt, 0)
            if state == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state == 0:
                found = visit(nxt)
                if found:
                    return found
        colour[node] = 2
        stack.pop()
        return None

    for node in sorted(edges):
        if colour.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None


def main():
    vanilla = vanilla_biomes()
    mod = mod_biomes()

    vanilla_cycle = find_cycle(edges_for(vanilla))
    if vanilla_cycle:
        print("vanilla cycle:")
        for node in vanilla_cycle:
            print("  %s @%d" % node)
        return 1

    biomes = dict(vanilla)
    biomes.update(mod)
    cycle = find_cycle(edges_for(biomes))

    if not cycle:
        print("no cycle over %d biomes (%d vanilla + %d mod)" % (len(biomes), len(vanilla), len(mod)))
        return 0

    print("cycle:")
    for node in cycle:
        print("  %s @%d" % node)
    return 1


if __name__ == "__main__":
    sys.exit(main())
