# Terrain Refreshed

![Terrain Refreshed](docs/banner.png)

[![Latest release](https://img.shields.io/github/v/release/ItsMeRevID/Terrain-Refreshed?label=release)](https://github.com/ItsMeRevID/Terrain-Refreshed/releases/latest)
[![Build](https://github.com/ItsMeRevID/Terrain-Refreshed/actions/workflows/build.yml/badge.svg)](https://github.com/ItsMeRevID/Terrain-Refreshed/actions/workflows/build.yml)

A Fabric mod that overhauls Minecraft's world generation: realistic terrain shaping, dramatic
mountains, flowing streams and rivers, 100 new biomes with hand-tuned colours, natural vegetation
and organically grown fancy trees.

| | |
|---|---|
| Author | RevSkyMC |
| Package | `net.revskymc.terrainrefreshed` |
| Minecraft | 26.3 |
| Loader | Fabric 0.20.1 |
| Fabric API | 0.165.2+26.3 |
| License | MIT |

## Features

- **Realistic terrain shape** — the overworld cheese density is replaced with a blended field of
  river carving, mountain lift, crag detail and rolling relief, so valleys, plateaus and ridges
  replace the vanilla hills.
- **Fancy mountains** — mountain height is masked against the continentalness and ridge noise, so
  ranges grow tall and craggy only where the terrain calls for them.
- **Streams** — a dedicated `terrainrefreshed:stream` feature carves a meandering channel into the
  surface, lays a gravel bed and fills it with water; the river density function carves the wider
  valleys the streams run through.
- **100 new biomes** — a full biome set with their own climate cells, grass/foliage/water colours
  and vegetation profiles. The biomes are injected into the overworld multi-noise source at runtime,
  so they replace the vanilla biomes of their climate cells instead of being appended to them.
- **Fancy biome colours** — every biome carries its own water, grass, foliage and dry-foliage
  tints, plus a sky colour attribute.
- **Natural vegetation** — ground cover, flowers, mushrooms, sugar cane, vines and lily pads are
  layered per biome family (meadow, forest, wetland, arid, rock, jungle, savanna).
- **Fancy trees** — `terrainrefreshed:fancy_tree` is one feature with nine silhouettes in
  `worldgen/TreeForm.java`, each built the way the real tree grows: `spreading` (leaning trunk,
  sideways limbs, blobby canopy), `conical` spruce whose whorls shorten as they climb, `pine` tiers
  upturned along a bare shaft, `weeping` willow curtains, `floral` tabebuya as one blossom dome on
  a clear stem, `umbrella` acacia flattened into a disc, `columnar` cypress that never widens,
  `baobab` with a four-log barrel and stubby arms, and `palm` with a leaning stem and eight drooping
  fronds. Leaf distances are computed from the real log positions. Eleven species use them:
  oak, birch, jungle (spreading), spruce (conical), pine, willow, acacia (umbrella), tabebuya
  (cherry blocks), cypress, baobab and palm.

## Layout

```
src/main/java/net/revskymc/terrainrefreshed/
  TerrainRefreshed.java          mod entrypoint, feature type registration
  mixin/                          runtime injection into the overworld biome source
  worldgen/
    FancyTreeFeature.java        custom tree feature
    TreeForm.java                the nine tree silhouettes the feature grows
    StreamFeature.java           custom stream feature
    OverworldBiomeExtender.java  carves the mod's climate cells out of the vanilla biome list
    BiomeClimateTable.java       generated climate table
src/main/resources/data/terrainrefreshed/worldgen/  biomes, features, noises, density functions
src/main/resources/data/minecraft/worldgen/density_function/  overworld terrain overrides
src/main/resources/assets/terrainrefreshed/icon.png  mod icon, referenced by fabric.mod.json
docs/banner.png  page banner for the mod hosts
tools/generate_content.py        single source of truth for the data-driven content
tools/check_feature_cycles.py    offline check for the game's feature order cycle check
tools/climate_audit.py           offline check of the climate volume each cell keeps
tools/band_rates.py              per-band locate hit rate measured from a sweep transcript
tools/smoke_density.py           searches biomes from several origins to measure real rarity
tools/smoke_trees.py             plants each species in the air and measures its silhouette
tools/smoke_test.sh              dedicated server smoke test driven over RCON
```

## Building

```bash
./gradlew build
```

The runnable jar is written to `build/libs/`.

## Content generation

All data-driven content is produced by `tools/generate_content.py`; edit the `BIOMES` table there
rather than the generated JSON.

```bash
python tools/generate_content.py
```

Each biome family mirrors the feature order of a vanilla biome, because the game's feature sorter
rejects a biome set in which two biomes list a shared feature in a different relative order. After
regenerating, verify the result offline:

```bash
python tools/check_feature_cycles.py
python tools/climate_audit.py
```

Climate cells are not free-floating. Every one is cut out of a (temperature, humidity,
continentalness, erosion) neighbourhood that vanilla itself occupies in the overworld list, captured
in `tools/vanilla_cells.txt`, and sits inside the weirdness and erosion windows the generator records
as measured. A hand-authored cell in a tail of the climate noise passes every structural check and
still never receives terrain, so the windows are the part that makes the biomes findable. Re-measure
them with the locate sweep and the per-band hit rate it implies:

```bash
bash tools/smoke_test.sh smoke terrainrefreshed-smoke 0 12 | tee run/smoke.locate.txt
python tools/band_rates.py run/smoke.locate.txt
```

## Smoke test

`tools/smoke_test.sh` boots the dev dedicated server, waits for the world to generate, then checks
over RCON that every new biome is reachable with `/locate biome`, that the custom tree and stream
features place successfully, which biome the multi-noise source picks at a few positions, and — with
`tools/smoke_trees.py` — that each species actually grows the silhouette its form is named after. The
probe plants every species in clear sky above the force-loaded area and walks the column upward with
`clone ... filtered <block> normal`, which counts the logs and leaves per level without touching the
tree, then asserts the shape: a spruce cone with its mass low, a pine bare for half its height, a
willow whose leaves hang below the crown, a tabebuya dome over a bare shaft, a flat acacia disc, a
cypress that never widens, a baobab four logs thick, a palm with fronds only at the top. The run
exits non-zero when a biome is missing or a species reads as the wrong shape.

```bash
bash tools/smoke_test.sh smoke                                  # full locate sweep
bash tools/smoke_test.sh smoke terrainrefreshed-smoke 0 12      # + density probe over 12 biomes
```

The optional fourth argument spreads that many biomes over the set and searches for each of them
from six origins tens of thousands of blocks apart, which separates a biome that is genuinely rare
from one that merely happened to sit far from that particular spawn point.

Against a running server that already force-loads `-64 -64 64 64`, the silhouette probe can be
re-run on its own: `python tools/smoke_trees.py 127.0.0.1 25575 <rcon-password>`. It clears each
probe column before planting, so it is repeatable.

## Releases

Every push to `main` is rebuilt by GitHub Actions, so the repository always carries the current
build. To ship a new version, change `version=` in `gradle.properties` and push: the tag, the
release title and the attached jar follow that file.

| Workflow | What it does |
|---|---|
| `build.yml` | builds the mod on every push and pull request and stores the jars as a workflow artifact |
| `release.yml` | builds on `main`, then creates or refreshes the release of the current version and replaces the attached jar |
| `modrinth.yml` | uploads the jar to Modrinth; the release workflow dispatches it right after the GitHub release is published |

The jar of the newest build is always at
<https://github.com/ItsMeRevID/Terrain-Refreshed/releases/latest>.

Publishing on Modrinth needs three things, once:

1. create the project page at <https://modrinth.com/mod/terrain-refreshed>
2. create an access token with the `write:versions` scope
3. add the token as the repository secret `MODRINTH_TOKEN` and the project slug as the
   repository variable `MODRINTH_PROJECT_ID`

Until the token is there, the Modrinth workflow reports that it skipped and the rest of the
pipeline stays green. `MODRINTH_GAME_VERSIONS` overrides the Minecraft versions the release
claims and defaults to `["26.3"]`.

## License

MIT — see [LICENSE](LICENSE).
