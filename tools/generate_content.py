#!/usr/bin/env python3
"""Generates the data-driven content of the Terrain Refreshed mod.

Outputs:
  src/main/resources/data/terrainrefreshed/worldgen/biome/*.json
  src/main/resources/data/terrainrefreshed/worldgen/feature/*.json
  src/main/resources/data/terrainrefreshed/worldgen/placed_feature/*.json
  src/main/resources/data/terrainrefreshed/worldgen/noise/*.json
  src/main/resources/data/terrainrefreshed/worldgen/density_function/*.json
  src/main/resources/data/minecraft/worldgen/density_function/overworld/sloped_cheese.json
  src/main/resources/assets/terrainrefreshed/lang/en_us.json
  src/main/java/net/revskymc/terrainrefreshed/worldgen/BiomeClimateTable.java

The single source of truth for the biome set is the BIOMES table below; the
Java climate table is emitted from it so the datapack biomes and the runtime
climate injection can never drift apart.

Every emitted cell is cut from a neighbourhood of the vanilla climate list, read from
tools/vanilla_cells.txt. That file is the overworld parameter list captured from a running 26.3
server: temporarily log every surface point of the vanilla list at injection time and keep the lines
the server writes as `VANILLA-CELL <biome> ParameterPoint[...]`. It is what keeps the new biomes
inside climate space the world noise actually reaches.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "main", "resources", "data")
MOD = "terrainrefreshed"

# ---------------------------------------------------------------- climate grid
# Vanilla overworld climate bands (OverworldBiomeBuilder). Each biome names one band per axis as
# its intended climate; the weirdness lane is then allocated from a populated vanilla neighbourhood
# that fits those bands. Temperature and humidity are honoured exactly, continentalness and erosion
# as well as the measured windows below allow, because those two axes decide how much terrain a cell
# actually gets.
TEMPERATURES = [(-1.0, -0.45), (-0.45, -0.15), (-0.15, 0.2), (0.2, 0.55), (0.55, 1.0)]
HUMIDITIES = [(-1.0, -0.35), (-0.35, -0.1), (-0.1, 0.1), (0.1, 0.3), (0.3, 1.0)]
CONTINENTALNESS = [(-0.19, -0.11), (-0.11, 0.03), (0.03, 0.3), (0.3, 1.0)]
EROSIONS = [
    (-1.0, -0.78),
    (-0.78, -0.375),
    (-0.375, -0.2225),
    (-0.2225, 0.05),
    (0.05, 0.45),
    (0.45, 0.55),
    (0.55, 1.0),
]

# ---------------------------------------------------------------- vanilla shelves
# The overworld climate list captured from a running 26.3 server. Vanilla only ever places land
# biomes in the (temperature, humidity, continentalness, erosion) neighbourhoods it occupies, and
# the weirdness lanes of each neighbourhood are the climate regions the world noise actually
# reaches. Anchoring every new cell to a neighbourhood, and to a lane that vanilla itself uses,
# is what makes a new biome reachable in the generated world.
VANILLA_DUMP = os.path.join(ROOT, "tools", "vanilla_cells.txt")
LINE = re.compile(r"VANILLA-CELL (\S+) ParameterPoint\[(.*)\]\s*$")
FIELD = re.compile(r"(\w+)=\[(-?\d+)-(-?\d+)\]")
CLIMATE_AXES = ("temperature", "humidity", "continentalness", "erosion", "weirdness")

# Measured with /locate biome from six origins spread over 40k blocks: every cell whose weirdness
# fell outside this window went unfound, because the weirdness noise is bell shaped and the tails
# carry almost no terrain. Cells inside it are as common as the vanilla lane they were carved from.
POPULAR_WEIRDNESS = (-0.4, 0.75)

# Same measurement over the erosion axis, on the full locate sweep from spawn: of the 73 cells whose
# erosion range sat inside this window 72 were found, of the 27 outside it only 14 were. Erosion
# above 0.45 is the over-eroded tail and below -0.4 the untouched peak tail; both carry so little
# terrain that a biome living there is never near a search origin.
POPULAR_EROSION = (-0.4, 0.45)

# Width of the weirdness lane every new biome gets. At this width a cell holds roughly the same
# share of its neighbourhood as one vanilla lane, which is what let the vanilla biome there be
# found within a few thousand blocks.
CELL_WIDTH = 0.2

# The frozen and hyper-arid bands sit in the tails of their noise, where the world leaves far less
# terrain, so a cell anchored there claims a wider lane; see lane_widths().
TAIL_CELL_WIDTH = 0.3
TAIL_BANDS = frozenset((TEMPERATURES[0], HUMIDITIES[0]))

# ------------------------------------------------------------------ vegetation
# The game's feature sorter chains the features of every biome into one graph and
# rejects it when two biomes list a shared feature in a different relative order.
# Every category therefore mirrors the feature order of a vanilla biome and only
# swaps the tree features for the fancy variants, which keeps our biomes and the
# vanilla ones cycle free.
ORE_FEATURES = [
    "minecraft:ore_dirt",
    "minecraft:ore_gravel",
    "minecraft:ore_granite_upper",
    "minecraft:ore_granite_lower",
    "minecraft:ore_diorite_upper",
    "minecraft:ore_diorite_lower",
    "minecraft:ore_andesite_upper",
    "minecraft:ore_andesite_lower",
    "minecraft:ore_tuff",
    "minecraft:ore_coal_upper",
    "minecraft:ore_coal_lower",
    "minecraft:ore_iron_upper",
    "minecraft:ore_iron_middle",
    "minecraft:ore_iron_small",
    "minecraft:ore_gold",
    "minecraft:ore_gold_lower",
    "minecraft:ore_redstone",
    "minecraft:ore_redstone_lower",
    "minecraft:ore_diamond",
    "minecraft:ore_diamond_medium",
    "minecraft:ore_diamond_large",
    "minecraft:ore_diamond_buried",
    "minecraft:ore_lapis",
    "minecraft:ore_lapis_buried",
    "minecraft:ore_copper",
    "minecraft:underwater_magma",
    "minecraft:disk_sand",
    "minecraft:disk_clay",
    "minecraft:disk_gravel",
]

SWAMP_ORES = ORE_FEATURES[:-3] + ["minecraft:disk_clay"]

CATEGORY_TEMPLATES = {
    "meadow": {
        "underground": ["minecraft:monster_room", "minecraft:monster_room_deep"],
        "surface": [],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:patch_tall_grass_2",
            "minecraft:patch_bush",
            "terrainrefreshed:fancy_oak_sparse",
            "minecraft:flower_plains",
            "minecraft:patch_grass_plain",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_pumpkin",
            "minecraft:patch_sugar_cane",
            "minecraft:patch_firefly_bush_near_water",
            "terrainrefreshed:fancy_tabebuya",
        ],
    },
    "forest": {
        "underground": ["minecraft:monster_room", "minecraft:monster_room_deep"],
        "surface": [],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:forest_flowers",
            "terrainrefreshed:fancy_oak",
            "minecraft:patch_bush",
            "minecraft:flower_default",
            "minecraft:patch_grass_forest",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_pumpkin",
            "minecraft:patch_sugar_cane",
            "minecraft:patch_firefly_bush_near_water",
            "terrainrefreshed:fancy_birch",
            "terrainrefreshed:fancy_pine",
            "terrainrefreshed:fancy_tabebuya",
        ],
    },
    "wetland": {
        "underground": [
            "minecraft:fossil_upper",
            "minecraft:fossil_lower",
            "minecraft:monster_room",
            "minecraft:monster_room_deep",
        ],
        "surface": [],
        "ores": SWAMP_ORES,
        "vegetation": [
            "minecraft:glow_lichen",
            "terrainrefreshed:fancy_willow",
            "minecraft:flower_swamp",
            "minecraft:patch_grass_normal",
            "minecraft:patch_dead_bush",
            "minecraft:patch_waterlily",
            "minecraft:brown_mushroom_swamp",
            "minecraft:red_mushroom_swamp",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_sugar_cane_swamp",
            "minecraft:patch_pumpkin",
            "minecraft:patch_firefly_bush_swamp",
            "minecraft:patch_firefly_bush_near_water_swamp",
            "minecraft:seagrass_swamp",
            "terrainrefreshed:fancy_palm",
            "terrainrefreshed:stream",
        ],
    },
    "arid": {
        "underground": [
            "minecraft:fossil_upper",
            "minecraft:fossil_lower",
            "minecraft:monster_room",
            "minecraft:monster_room_deep",
        ],
        "surface": ["minecraft:desert_well"],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:flower_default",
            "minecraft:patch_grass_badlands",
            "minecraft:patch_dry_grass_desert",
            "minecraft:patch_dead_bush_2",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_sugar_cane_desert",
            "minecraft:patch_pumpkin",
            "minecraft:patch_cactus_desert",
            "terrainrefreshed:fancy_palm",
            "terrainrefreshed:fancy_cypress",
        ],
    },
    "rock": {
        "underground": ["minecraft:monster_room", "minecraft:monster_room_deep"],
        "surface": [],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:patch_large_fern",
            "terrainrefreshed:fancy_spruce",
            "minecraft:flower_default",
            "minecraft:patch_grass_taiga_2",
            "minecraft:brown_mushroom_taiga",
            "minecraft:red_mushroom_taiga",
            "minecraft:patch_pumpkin",
            "minecraft:patch_sugar_cane",
            "minecraft:patch_firefly_bush_near_water",
            "minecraft:patch_berry_common",
            "terrainrefreshed:fancy_pine",
            "terrainrefreshed:fancy_cypress",
        ],
    },
    "jungle": {
        "underground": ["minecraft:monster_room", "minecraft:monster_room_deep"],
        "surface": [],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:bamboo_light",
            "terrainrefreshed:fancy_jungle",
            "minecraft:flower_warm",
            "minecraft:patch_grass_jungle",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_pumpkin",
            "minecraft:patch_sugar_cane",
            "minecraft:patch_firefly_bush_near_water",
            "minecraft:vines",
            "minecraft:patch_melon",
            "terrainrefreshed:fancy_palm",
        ],
    },
    "savanna": {
        "underground": ["minecraft:monster_room", "minecraft:monster_room_deep"],
        "surface": [],
        "ores": ORE_FEATURES,
        "vegetation": [
            "minecraft:glow_lichen",
            "minecraft:patch_tall_grass",
            "terrainrefreshed:fancy_acacia",
            "terrainrefreshed:fancy_baobab",
            "minecraft:flower_warm",
            "minecraft:patch_grass_savanna",
            "minecraft:brown_mushroom_normal",
            "minecraft:red_mushroom_normal",
            "minecraft:patch_pumpkin",
            "minecraft:patch_sugar_cane",
            "minecraft:patch_firefly_bush_near_water",
        ],
    },
}



def biome(bid, name, cat, t, h, c, e, temp, downfall, precip,
          water="#3f76e4", foliage=None, dry=None, grass=None, gcm="none",
          sky="#78a7ff", extra=None):
    return {
        "id": bid,
        "name": name,
        "cat": cat,
        "t": t, "h": h, "c": c, "e": e,
        "temp": temp,
        "downfall": downfall,
        "precip": precip,
        "water": water,
        "foliage": foliage,
        "dry": dry,
        "grass": grass,
        "gcm": gcm,
        "sky": sky,
        "extra": extra or [],
    }


# --------------------------------------------------------------------- biomes
# (t, h, c, e) pick the climate neighbourhood the biome belongs to. The weirdness lane is not
# authored here: allocate_cells() cuts it out of a lane vanilla itself occupies, so every biome
# lands on climate space the world noise actually visits.
BIOMES = [
    # --- Grasslands & meadows ------------------------------------------------
    biome("sunlit_meadow", "Sunlit Meadow", "meadow", 2, 2, 2, 3, 0.7, 0.4, True,
          grass="#a8d85f", foliage="#8cc45a"),
    biome("golden_grassland", "Golden Grassland", "meadow", 2, 1, 2, 3, 0.8, 0.3, True,
          grass="#d0c257", foliage="#b3b45c", dry="#d3c05a"),
    biome("wildflower_plains", "Wildflower Plains", "meadow", 2, 3, 2, 4, 0.8, 0.5, True,
          grass="#9fd158", foliage="#8cc45a"),
    biome("bloomstep_meadow", "Bloomstep Meadow", "meadow", 1, 2, 1, 3, 0.4, 0.6, True,
          grass="#a2d05c", foliage="#8cc45a"),
    biome("clover_heath", "Clover Heath", "meadow", 1, 1, 1, 4, 0.4, 0.7, True,
          grass="#9ac95a", foliage="#87bf58"),
    biome("dewy_prairie", "Dewy Prairie", "meadow", 2, 4, 2, 3, 0.7, 0.8, True,
          grass="#9fd35c", foliage="#88c157"),
    biome("highland_heath", "Highland Heath", "meadow", 1, 3, 3, 1, 0.2, 0.6, True,
          grass="#8fbd57", foliage="#7fae54"),
    biome("sagebrush_steppe", "Sagebrush Steppe", "meadow", 2, 0, 2, 4, 0.9, 0.2, False,
          grass="#b2b169", foliage="#9aa563", dry="#c4b56b"),
    biome("misty_meadow", "Misty Meadow", "meadow", 1, 2, 1, 2, 0.4, 0.8, True,
          grass="#9bce63", foliage="#87c25e", sky="#9fc0e8"),
    biome("frostgrass_tundra", "Frostgrass Tundra", "meadow", 0, 2, 2, 3, -0.3, 0.3, True,
          grass="#9ec5a0", foliage="#8bb894", sky="#a8c4e6"),
    biome("snowless_winter", "Snowless Winter", "meadow", 0, 1, 1, 3, -0.2, 0.4, True,
          grass="#c3d4c8", foliage="#a9c0a4", sky="#b9cfe4"),
    biome("aurora_grassland", "Aurora Grassland", "meadow", 0, 3, 3, 3, -0.4, 0.4, True,
          grass="#a9d3a2", foliage="#93bd8f", sky="#7fb4d8"),
    biome("windy_plateau", "Windy Plateau", "meadow", 2, 0, 3, 4, 0.9, 0.3, True,
          grass="#b0b767", foliage="#9aa35e", dry="#c0ad66"),
    biome("silver_meadow", "Silver Meadow", "meadow", 1, 4, 1, 3, 0.3, 0.6, True,
          grass="#b9d2a2", foliage="#9ec088", dry="#c2bd8f"),
    biome("ember_field", "Ember Field", "meadow", 3, 0, 2, 5, 1.2, 0.1, False,
          grass="#c98f52", foliage="#a97a4c", dry="#c98245"),
    biome("verdant_flats", "Verdant Flats", "meadow", 2, 3, 1, 3, 0.7, 0.5, True,
          grass="#a3d75e", foliage="#8fc75a"),
    biome("goldenrod_hills", "Goldenrod Hills", "meadow", 2, 4, 2, 2, 0.8, 0.5, True,
          grass="#c8c463", foliage="#adb259", dry="#c8b95c"),
    biome("dry_grassland", "Dry Grassland", "meadow", 3, 1, 2, 5, 1.1, 0.2, False,
          grass="#c3b26b", foliage="#a89f5f", dry="#cbb069"),
    biome("moonlight_meadow", "Moonlight Meadow", "meadow", 0, 2, 3, 2, -0.4, 0.5, True,
          grass="#a8c6ac", foliage="#8fb294", sky="#8fb0d4"),

    # --- Forests & woodlands -------------------------------------------------
    biome("sunlit_grove", "Sunlit Grove", "forest", 2, 2, 2, 3, 0.7, 0.6, True,
          grass="#9ccf58", foliage="#7fb84f"),
    biome("amberwood_forest", "Amberwood Forest", "forest", 2, 2, 2, 4, 0.8, 0.6, True,
          grass="#b0bd5e", foliage="#9c9e4f", dry="#c2a44f"),
    biome("misty_pines", "Misty Pines", "forest", 1, 3, 2, 3, 0.3, 0.8, True,
          grass="#8fbe6a", foliage="#77a95a", sky="#9dbde2"),
    biome("birchwood_glade", "Birchwood Glade", "forest", 1, 2, 1, 3, 0.5, 0.6, True,
          grass="#a9d472", foliage="#8fc063"),
    biome("crimson_hollow", "Crimson Hollow", "forest", 2, 2, 3, 5, 0.7, 0.7, True,
          grass="#a5834f", foliage="#a2503c", dry="#a8703c"),
    biome("frostpine_wood", "Frostpine Wood", "forest", 0, 3, 2, 3, -0.4, 0.6, True,
          grass="#a4c6a8", foliage="#84a78c", dry="#b4b79a"),
    biome("golden_birchwood", "Golden Birchwood", "forest", 1, 2, 2, 3, 0.6, 0.5, True,
          grass="#c1cd6a", foliage="#a9b154", dry="#c6b256"),
    biome("emerald_thicket", "Emerald Thicket", "forest", 2, 3, 1, 3, 0.8, 0.8, True,
          grass="#8fd05a", foliage="#71b34a"),
    biome("silent_woodland", "Silent Woodland", "forest", 1, 3, 3, 2, 0.3, 0.7, True,
          grass="#93bd67", foliage="#7ea35a", sky="#a3c0e0"),
    biome("copperwood", "Copperwood", "forest", 2, 1, 3, 3, 0.9, 0.4, True,
          grass="#b3a55e", foliage="#9c8f4e", dry="#bb9750"),
    biome("bluewood_forest", "Bluewood Forest", "forest", 1, 4, 2, 3, 0.4, 0.9, True,
          grass="#96c877", foliage="#7fb063"),
    biome("silverleaf_wood", "Silverleaf Wood", "forest", 1, 4, 3, 2, 0.2, 0.7, True,
          grass="#b6d3a4", foliage="#9db98a"),
    biome("gloommoss_forest", "Gloommoss Forest", "forest", 2, 4, 2, 5, 0.7, 0.9, True,
          grass="#7ba85c", foliage="#66914a", gcm="dark_forest"),
    biome("firefly_wood", "Firefly Wood", "forest", 2, 3, 1, 4, 0.8, 0.8, True,
          grass="#9ad264", foliage="#7fbb52", sky="#8fb8dd"),
    biome("redwood_grove", "Redwood Grove", "forest", 2, 3, 3, 2, 0.8, 0.7, True,
          grass="#8cb862", foliage="#74a04f"),
    biome("highland_pinewood", "Highland Pinewood", "forest", 0, 2, 3, 1, -0.3, 0.5, True,
          grass="#93b98b", foliage="#7c9f78"),
    biome("warm_hollow", "Warm Hollow", "forest", 3, 2, 2, 3, 1.0, 0.6, True,
          grass="#9ac95a", foliage="#7fb54c"),
    biome("ancient_stand", "Ancient Stand", "forest", 2, 2, 3, 5, 0.7, 0.6, True,
          grass="#8fbe5c", foliage="#77a44b"),
    biome("starlit_wood", "Starlit Wood", "forest", 0, 3, 2, 4, -0.3, 0.6, True,
          grass="#a3c7ac", foliage="#8aa78f", sky="#87a8d6"),

    # --- Wetlands & waters ----------------------------------------------------
    biome("reed_marsh", "Reed Marsh", "wetland", 2, 3, 1, 4, 0.8, 0.9, True,
          water="#4a6f52", grass="#8aa85c", foliage="#7f9c55"),
    biome("willow_fen", "Willow Fen", "wetland", 2, 4, 1, 3, 0.8, 0.9, True,
          water="#47695b", grass="#93b96b", foliage="#82a45c"),
    biome("misty_lagoon", "Misty Lagoon", "wetland", 2, 4, 1, 2, 0.8, 0.9, True,
          water="#3f6f8a", grass="#8cb877", foliage="#7ba165"),
    biome("mossy_bog", "Mossy Bog", "wetland", 1, 4, 1, 5, 0.3, 0.9, True,
          water="#41614c", grass="#6f9359", foliage="#5f834d", gcm="swamp"),
    biome("crystal_lake", "Crystal Lake", "wetland", 1, 2, 0, 3, 0.4, 0.7, True,
          water="#3f8fd4", grass="#9ccf66", foliage="#84bd56"),
    biome("flooded_plain", "Flooded Plain", "wetland", 2, 4, 1, 5, 0.9, 0.9, True,
          water="#48706b", grass="#95bb6a", foliage="#84a55c"),
    biome("tea_water_marsh", "Tea-Water Marsh", "wetland", 2, 3, 0, 3, 0.9, 0.9, True,
          water="#5a6f4f", grass="#8ca45e", foliage="#7d9553"),
    biome("frost_lake", "Frost Lake", "wetland", 0, 3, 0, 3, -0.4, 0.7, True,
          water="#3d57d6", grass="#a3c7b4", foliage="#8bab99"),
    biome("mangrove_edge", "Mangrove Edge", "wetland", 3, 4, 0, 4, 1.1, 0.9, True,
          water="#3d7a6b", grass="#8fb765", foliage="#7ba25a"),
    biome("peat_moor", "Peat Moor", "wetland", 1, 3, 1, 5, 0.3, 0.9, True,
          water="#4a5f52", grass="#7c9260", foliage="#6d8253"),
    biome("winter_marsh", "Winter Marsh", "wetland", 0, 2, 1, 4, -0.3, 0.7, True,
          water="#43658c", grass="#a8c4b6", foliage="#91ab99"),
    biome("red_marsh", "Red Marsh", "wetland", 3, 4, 1, 4, 1.1, 0.9, True,
          water="#6b4a4a", grass="#a08a5c", foliage="#8d7a50"),
    biome("drowned_meadow", "Drowned Meadow", "wetland", 2, 4, 0, 4, 0.8, 0.9, True,
          water="#3f7f96", grass="#87b76c", foliage="#78a05c"),
    biome("amber_marsh", "Amber Marsh", "wetland", 3, 3, 1, 5, 1.0, 0.8, True,
          water="#7a6a45", grass="#b0a45f", foliage="#9d9250", dry="#bda85b"),
    biome("quiet_backwater", "Quiet Backwater", "wetland", 2, 3, 1, 3, 0.8, 0.9, True,
          water="#416e6e", grass="#94bb6c", foliage="#84a65e"),
    biome("frostwater_fen", "Frostwater Fen", "wetland", 0, 4, 1, 4, -0.5, 0.8, True,
          water="#4a6d8a", grass="#a7c8ba", foliage="#95ae9e"),
    biome("river_meadow", "River Meadow", "wetland", 2, 3, 2, 4, 0.9, 0.8, True,
          water="#3f86a8", grass="#9ed169", foliage="#87c05a"),

    # --- Arid lands & savannas -----------------------------------------------
    biome("amber_dunes", "Amber Dunes", "arid", 3, 0, 2, 4, 1.2, 0.1, False,
          grass="#cbb063", foliage="#b09a55", dry="#d3b45c", water="#3f8f9d"),
    biome("salt_flats", "Salt Flats", "arid", 3, 0, 1, 5, 1.3, 0.0, False,
          grass="#d3cf9f", foliage="#b3ae7d", dry="#dcd6a8", water="#5fb0b8"),
    biome("ochre_plateau", "Ochre Plateau", "arid", 3, 1, 3, 4, 1.2, 0.2, False,
          grass="#bb9a5c", foliage="#a4874c", dry="#c79f57"),
    biome("sunbaked_basin", "Sunbaked Basin", "arid", 3, 0, 2, 5, 1.4, 0.0, False,
          grass="#c2a15e", foliage="#a98c4f", dry="#cfa75c"),
    biome("crimson_badlands", "Crimson Badlands", "arid", 3, 0, 3, 4, 1.3, 0.2, False,
          grass="#bd6f4c", foliage="#a65c40", dry="#c8734a"),
    biome("pale_ashland", "Pale Ashland", "arid", 2, 0, 3, 5, 1.0, 0.1, False,
          grass="#c3b8a3", foliage="#a79c88", dry="#cec3ad"),
    biome("savanna_grassland", "Savanna Grassland", "savanna", 3, 1, 2, 3, 1.0, 0.4, True,
          grass="#bfb755", foliage="#a6a24f", dry="#c4b45a"),
    biome("acacia_woodland", "Acacia Woodland", "savanna", 3, 1, 2, 4, 1.1, 0.3, False,
          grass="#b9b25c", foliage="#a09c4f", dry="#c0ae56"),
    biome("golden_scrub", "Golden Scrub", "savanna", 3, 0, 2, 4, 1.1, 0.2, False,
          grass="#c6b25f", foliage="#ac9f51", dry="#d0b95f"),
    biome("windswept_scrub", "Windswept Scrub", "savanna", 3, 2, 3, 4, 1.0, 0.4, True,
          grass="#b7b45f", foliage="#a19f52", dry="#c2b158"),
    biome("red_scrubland", "Red Scrubland", "arid", 3, 1, 3, 3, 1.2, 0.2, False,
          grass="#bd8a52", foliage="#a5744a", dry="#c78f52"),
    biome("dune_sea", "Dune Sea", "arid", 3, 0, 2, 5, 1.3, 0.1, False,
          grass="#cdb266", foliage="#b29c58", dry="#d8bb5f"),
    biome("dry_barrens", "Dry Barrens", "arid", 2, 0, 3, 5, 1.0, 0.2, False,
          grass="#bcae68", foliage="#a49a57", dry="#c4b268"),
    biome("sunstone_expanse", "Sunstone Expanse", "arid", 3, 2, 2, 4, 1.2, 0.2, False,
          grass="#c8a962", foliage="#ad9150", dry="#d3b15c"),
    biome("arid_flats", "Arid Flats", "arid", 3, 1, 1, 4, 1.1, 0.2, False,
          grass="#c0b067", foliage="#a79b56", dry="#c9b365"),
    biome("thorn_desert", "Thorn Desert", "arid", 3, 0, 2, 3, 1.2, 0.1, False,
          grass="#b8a862", foliage="#9f9350", dry="#c4ac5d"),
    biome("riverbed_badlands", "Riverbed Badlands", "arid", 3, 1, 2, 6, 1.1, 0.2, False,
          grass="#c19f60", foliage="#a68a4f", dry="#c8a45c"),
    biome("scorched_plateau", "Scorched Plateau", "arid", 3, 2, 3, 4, 1.3, 0.1, False,
          grass="#b5824f", foliage="#9c6e44", dry="#c08b53"),
    biome("dust_plain", "Dust Plain", "arid", 3, 1, 2, 4, 1.1, 0.3, False,
          grass="#c3ae62", foliage="#a89a51", dry="#cbb663"),
    biome("fossil_flats", "Fossil Flats", "arid", 3, 0, 1, 6, 1.3, 0.0, False,
          grass="#c9bda0", foliage="#aca288", dry="#d2c6a8"),
    biome("copper_canyon", "Copper Canyon", "arid", 3, 1, 3, 3, 1.2, 0.2, False,
          grass="#b88457", foliage="#9f6f47", dry="#c08a56"),
    biome("hazy_rainforest", "Hazy Rainforest", "jungle", 3, 4, 2, 3, 1.0, 0.9, True,
          grass="#68b23f", foliage="#3f8f34"),
    biome("verdant_rainforest", "Verdant Rainforest", "jungle", 3, 4, 2, 4, 1.0, 0.9, True,
          grass="#6cb740", foliage="#439534"),
    biome("bamboo_jungle_edge", "Bamboo Jungle Edge", "jungle", 3, 4, 1, 3, 1.0, 0.9, True,
          grass="#74bb45", foliage="#4b9a39"),
    biome("dense_canopy", "Dense Canopy", "jungle", 3, 3, 2, 3, 1.0, 0.9, True,
          grass="#63ac3e", foliage="#3c8b33"),
    biome("misty_rainforest", "Misty Rainforest", "jungle", 3, 4, 1, 4, 1.0, 0.9, True,
          grass="#6cb645", foliage="#439435", sky="#93b8dc"),

    # --- Rocky highlands & peaks ---------------------------------------------
    biome("granite_slopes", "Granite Slopes", "rock", 1, 2, 3, 1, 0.1, 0.5, True,
          grass="#8fb86a", foliage="#78a057"),
    biome("alpine_meadow", "Alpine Meadow", "rock", 0, 2, 3, 2, -0.4, 0.6, True,
          grass="#a3c396", foliage="#8aab80"),
    biome("frostpeak_ridge", "Frostpeak Ridge", "rock", 0, 1, 3, 1, -0.6, 0.5, True,
          grass="#bcd0c9", foliage="#a3b8b0"),
    biome("highland_bogs", "Highland Bogs", "rock", 0, 3, 3, 3, -0.3, 0.8, True,
          grass="#93ae83", foliage="#7d9a6f"),
    biome("windswept_heights", "Windswept Heights", "rock", 0, 2, 3, 3, -0.2, 0.5, True,
          grass="#9ab88c", foliage="#83a075"),
    biome("cloudpine_slope", "Cloudpine Slope", "rock", 0, 2, 3, 4, -0.5, 0.7, True,
          grass="#b0c7b2", foliage="#9ab39c"),
    biome("black_peaks", "Black Peaks", "rock", 1, 1, 3, 6, 0.1, 0.4, True,
          grass="#7f8f7a", foliage="#6b7c68"),
    biome("snowcapped_heights", "Snowcapped Heights", "rock", 0, 1, 3, 6, -0.7, 0.4, True,
          grass="#d2e0dd", foliage="#b9ccc7"),
    biome("mountain_meadow", "Mountain Meadow", "rock", 1, 2, 3, 3, 0.0, 0.7, True,
          grass="#9dc184", foliage="#87a970"),
    biome("boulder_wastes", "Boulder Wastes", "rock", 3, 0, 3, 5, 0.9, 0.3, False,
          grass="#a8a478", foliage="#8f8d61", dry="#b6aa7c"),
    # cold rather than frozen: a peak climate anchored in the frozen tail of the temperature noise
    # never came up inside the locate search radius, so this one sits one band warmer
    biome("fogbound_peak", "Fogbound Peak", "rock", 1, 4, 3, 2, -0.6, 0.7, True,
         grass="#b4c9c4", foliage="#9db3ac", sky="#a9c3e2"),
    biome("jagged_foothills", "Jagged Foothills", "rock", 1, 0, 3, 3, 0.5, 0.4, True,
         grass="#a3b379", foliage="#8c9f67"),
    biome("emerald_cliffs", "Emerald Cliffs", "rock", 1, 3, 3, 2, 0.3, 0.7, True,
         grass="#8fc478", foliage="#77a862"),
    biome("cold_heights", "Cold Heights", "rock", 0, 2, 3, 6, -0.6, 0.6, True,
         grass="#b6c8c2", foliage="#a1b5ad"),
    biome("gorge_terraces", "Gorge Terraces", "rock", 1, 2, 3, 4, 0.4, 0.5, True,
         grass="#9fbb7d", foliage="#88a76b"),
    biome("snowline_ridge", "Snowline Ridge", "rock", 0, 3, 3, 5, -0.7, 0.5, True,
         grass="#c6d6d2", foliage="#aec2bb"),
    biome("stonewind_heights", "Stonewind Heights", "rock", 0, 1, 3, 2, -0.3, 0.5, True,
         grass="#a6b598", foliage="#8ea080"),
    biome("highland_gorge", "Highland Gorge", "rock", 1, 3, 3, 1, 0.1, 0.6, True,
         grass="#93b774", foliage="#7da263"),
    biome("far_horizon", "Far Horizon", "rock", 0, 0, 3, 6, -0.5, 0.4, True,
         grass="#b0c3b4", foliage="#9bb0a1"),
]

assert len(BIOMES) == 100, "expected exactly 100 biomes, got %d" % len(BIOMES)
assert len({b["id"] for b in BIOMES}) == 100, "duplicate biome id"


# ------------------------------------------------------------------- helpers


def read_shelves():
    """Collect the vanilla land neighbourhoods and the weirdness lanes each one occupies."""
    lanes = {}
    for line in open(VANILLA_DUMP, encoding="utf-8"):
        match = LINE.search(line)
        if not match:
            continue
        fields = dict((name, (int(low), int(high))) for name, low, high in FIELD.findall(match.group(2)))
        temperature, humidity, continentalness, erosion, weirdness = (fields[name] for name in CLIMATE_AXES)
        # Anything that tops out below -0.45 continentalness is open water; those lanes belong to the
        # ocean biomes and a land biome carved from one would never be reachable from the surface.
        if continentalness[1] <= -4500:
            continue
        lanes.setdefault((temperature, humidity, continentalness, erosion), set()).add(weirdness)

    shelves = []
    for key in sorted(lanes):
        if not inside(key[3], POPULAR_EROSION):
            continue
        intervals = trim(merge(lanes[key]), POPULAR_WEIRDNESS)
        if sum(high - low for low, high in intervals) >= CELL_WIDTH * 10000:
            shelves.append(Shelf(key, intervals))
    return shelves


def inside(span, window):
    """Whether a climate range sits wholly inside a measured window on its axis."""
    low, high = (int(value * 10000) for value in window)
    return span[0] >= low and span[1] <= high


class Shelf:
    """One vanilla neighbourhood, with its available weirdness lanes consumed as cells are taken."""

    def __init__(self, ranges, intervals):
        self.ranges = ranges
        self.intervals = [[low, high] for low, high in intervals]

    @property
    def coverage(self):
        return sum(high - low for low, high in self.intervals)

    @property
    def longest(self):
        """Widest single lane left, which is what decides whether a tail biome fits here."""
        return max((high - low for low, high in self.intervals), default=0)

    def take(self, width):
        """Cut the next lane of the requested width off the front of the first interval that fits."""
        for interval in self.intervals:
            if interval[1] - interval[0] >= width:
                low = interval[0]
                interval[0] += width
                return (low, low + width)
        return None


def merge(lanes):
    merged = []
    for low, high in sorted(lanes):
        if merged and low <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    return [(low, high) for low, high in merged]


def trim(intervals, window):
    low_bound, high_bound = (int(value * 10000) for value in window)
    trimmed = []
    for low, high in intervals:
        clipped = (max(low, low_bound), min(high, high_bound))
        if clipped[0] < clipped[1]:
            trimmed.append(clipped)
    return trimmed


def score(shelf, intent):
    """
    Ranking used when several neighbourhoods suit a biome.

    exact  the neighbourhood sits in the temperature and humidity band the biome was written for
    fitted how many axes hold the intended band wholly inside them, so the climate stays the one the
           biome is named for
    spread how wide the continentalness and erosion bands are, because a wide band is visited by far
           more of the terrain noise than a narrow one, which is what makes a biome common enough to
           be found from spawn
    """
    wanted = intent[:4]
    exact = all(shelf.ranges[index] == wanted[index] for index in range(2))
    fitted = sum(1 for index in range(4) if contains(shelf.ranges[index], wanted[index]))
    spread = sum(shelf.ranges[index][1] - shelf.ranges[index][0] for index in range(2, 4))
    return (exact, fitted, spread)


def contains(outer, inner):
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def quantised(ranges):
    return [(int(low * 10000), int(high * 10000)) for low, high in ranges]


def allocate_cells(biomes, shelves):
    """Give every biome a cell cut from a neighbourhood vanilla itself occupies."""
    assigned = []
    report = []

    for b in biomes:
        intent = quantised([TEMPERATURES[b["t"]], HUMIDITIES[b["h"]],
                            CONTINENTALNESS[b["c"]], EROSIONS[b["e"]]])
        fits = sorted(
            (-rating[1], -rating[2], -shelf.longest, -shelf.coverage, shelf.ranges, shelf)
            for rating, shelf in ((score(shelf, intent), shelf) for shelf in shelves)
            if rating[0]
        )
        candidates = [fit[-1] for fit in fits]

        for shelf in candidates:
            cell = next_available(shelf, assigned, lane_widths(b))
            if cell:
                assigned.append(cell)
                b["cell"] = cell
                report.append((b["id"], shelf.ranges, cell[4]))
                break
        else:
            raise SystemExit("no vanilla neighbourhood left for biome %s" % b["id"])

    assert len({c for c in assigned}) == len(biomes), "duplicate biome climate cell"
    assert not any(
        intersects(cell, other) for index, cell in enumerate(assigned) for other in assigned[index + 1:]
    ), "overlapping biome climate cells leave the later biome without terrain"

    return report


def lane_widths(biome):
    """
    Weirdness widths to try for a biome, widest first.

    The frozen temperature band and the hyper-arid humidity band are tails of their noise, so a cell
    anchored there starts out rare: those were the farthest findings in the locate sweep, 4.4k to
    6.8k blocks against a 1.4k median, and the only outright miss. A wider lane is what brings a
    polar or desert biome back within reach of a random spawn point, and the standard width stays as
    the fallback for the neighbourhoods that have that much weirdness to spare.
    """
    bands = (TEMPERATURES[biome["t"]], HUMIDITIES[biome["h"]])
    widths = [TAIL_CELL_WIDTH, CELL_WIDTH] if any(band in TAIL_BANDS for band in bands) else [CELL_WIDTH]
    return [int(width * 10000) for width in widths]


def next_available(shelf, assigned, widths):
    """Cut the widest lane the shelf can still spare, skipping anything that collides with a given cell."""
    for width in widths:
        while True:
            weirdness = shelf.take(width)
            if weirdness is None:
                break
            cell = tuple(list(shelf.ranges) + [weirdness])
            if not any(intersects(cell, other) for other in assigned):
                return cell
    return None


def intersects(a, b):
    return all(not (left[1] <= right[0] or right[1] <= left[0]) for left, right in zip(a, b))


def fmt(v):
    return ("%.10g" % v)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")


def biome_features(b):
    template = CATEGORY_TEMPLATES[b["cat"]]
    steps = [[] for _ in range(11)]
    steps[1] = ["minecraft:lake_lava_underground", "minecraft:lake_lava_surface"]
    steps[2] = ["minecraft:amethyst_geode"]
    steps[3] = list(template["underground"])
    steps[4] = list(template["surface"])
    steps[6] = list(template["ores"])
    steps[8] = ["minecraft:spring_water", "minecraft:spring_lava"]
    steps[9] = list(template["vegetation"]) + list(b["extra"])
    steps[10] = ["minecraft:freeze_top_layer"]
    return steps


def biome_json(b):
    effects = {"water_color": b["water"]}
    if b["foliage"]:
        effects["foliage_color"] = b["foliage"]
    if b["dry"]:
        effects["dry_foliage_color"] = b["dry"]
    if b["grass"]:
        effects["grass_color"] = b["grass"]
    if b["gcm"] != "none":
        effects["grass_color_modifier"] = b["gcm"]
    doc = {
        "attributes": {"minecraft:visual/sky_color": b["sky"]},
        "carvers": ["minecraft:cave", "minecraft:cave_extra_underground", "minecraft:canyon"],
        "downfall": b["downfall"],
        "effects": effects,
        "features": biome_features(b),
        "has_precipitation": b["precip"],
        "temperature": b["temp"],
    }
    return doc


# --------------------------------------------------------------- terrain data
NOISES = {
    "river": {"base_amplitude": 0.9, "base_octave": -7, "octave_count": 6,
              "amplitude_modifiers": [1.0, 2.0, 2.0, 1.0, 1.0, 1.0]},
    "crag": {"base_amplitude": 1.0, "base_octave": -12, "octave_count": 8,
             "amplitude_modifiers": [1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0]},
    "detail": {"base_amplitude": 0.8, "base_octave": -11, "octave_count": 7,
               "amplitude_modifiers": [1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0]},
}


def density_functions():
    df = {}

    # --- streams: a meandering channel carved into the terrain ---------------
    df["river_noise"] = {
        "type": "minecraft:noise",
        "noise": "terrainrefreshed:river",
        "shift_x": "minecraft:shift_x",
        "shift_z": "minecraft:shift_z",
        "xz_scale": 0.0009,
        "y_scale": 0.0,
    }
    df["river_distance"] = {
        "type": "minecraft:abs",
        "input": "terrainrefreshed:river_noise",
    }
    df["river_channel"] = {
        "type": "minecraft:range_choice",
        "input": "terrainrefreshed:river_distance",
        "min_inclusive": 0.0,
        "max_exclusive": 0.035,
        "when_in_range": {"type": "minecraft:constant", "value": 1.0},
        "when_out_of_range": {"type": "minecraft:constant", "value": 0.0},
    }
    df["river_vertical"] = {
        "type": "minecraft:mul",
        "left": {
            "type": "minecraft:gradient",
            "axis": "y",
            "from_coordinate": 44,
            "from_value": 0.0,
            "to_coordinate": 58,
            "to_value": 1.0,
        },
        "right": {
            "type": "minecraft:gradient",
            "axis": "y",
            "from_coordinate": 104,
            "from_value": 1.0,
            "to_coordinate": 148,
            "to_value": 0.0,
        },
    }
    df["river_carve"] = {
        "type": "minecraft:mul",
        "left": "terrainrefreshed:river_channel",
        "right": {
            "type": "minecraft:mul",
            "left": "terrainrefreshed:river_vertical",
            "right": -1.15,
        },
    }

    # --- fancy mountains: taller, craggier peaks ---------------------------
    df["mountain_mask"] = {
        "type": "minecraft:mul",
        "left": {
            "type": "minecraft:spline",
            "spline": {
                "coordinate": "minecraft:overworld/continents",
                "points": [
                    {"derivative": 0.0, "location": -0.19, "value": 0.0},
                    {"derivative": 0.0, "location": 0.12, "value": 0.0},
                    {"derivative": 0.0, "location": 0.42, "value": 0.55},
                    {"derivative": 0.0, "location": 1.0, "value": 1.0},
                ],
            },
        },
        "right": {
            "type": "minecraft:spline",
            "spline": {
                "coordinate": "minecraft:overworld/ridges_folded",
                "points": [
                    {"derivative": 0.0, "location": -1.0, "value": 0.0},
                    {"derivative": 0.0, "location": 0.25, "value": 0.0},
                    {"derivative": 0.0, "location": 0.72, "value": 1.0},
                    {"derivative": 0.0, "location": 1.0, "value": 1.0},
                ],
            },
        },
    }
    df["mountain_lift"] = {
        "type": "minecraft:mul",
        "left": "terrainrefreshed:mountain_mask",
        "right": 2.35,
    }
    df["crag_noise"] = {
        "type": "minecraft:noise",
        "noise": "terrainrefreshed:crag",
        "shift_x": "minecraft:shift_x",
        "shift_z": "minecraft:shift_z",
        "xz_scale": 0.0035,
        "y_scale": 0.0,
    }
    df["crag_detail"] = {
        "type": "minecraft:mul",
        "left": {
            "type": "minecraft:mul",
            "left": "terrainrefreshed:mountain_mask",
            "right": "terrainrefreshed:crag_noise",
        },
        "right": 0.75,
    }
    df["detail_noise"] = {
        "type": "minecraft:noise",
        "noise": "terrainrefreshed:detail",
        "shift_x": "minecraft:shift_x",
        "shift_z": "minecraft:shift_z",
        "xz_scale": 0.0007,
        "y_scale": 0.00035,
    }
    df["rolling_relief"] = {
        "type": "minecraft:mul",
        "left": {
            "type": "minecraft:mul",
            "left": "terrainrefreshed:detail_noise",
            "right": {
                "type": "minecraft:spline",
                "spline": {
                    "coordinate": "minecraft:overworld/erosion",
                    "points": [
                        {"derivative": 0.0, "location": -1.0, "value": 1.0},
                        {"derivative": 0.0, "location": 0.0, "value": 0.55},
                        {"derivative": 0.0, "location": 1.0, "value": 0.3},
                    ],
                },
            },
        },
        "right": 0.55,
    }
    df["terrain_features"] = {
        "type": "minecraft:add",
        "left": "terrainrefreshed:river_carve",
        "right": {
            "type": "minecraft:add",
            "left": "terrainrefreshed:mountain_lift",
            "right": {
                "type": "minecraft:add",
                "left": "terrainrefreshed:crag_detail",
                "right": "terrainrefreshed:rolling_relief",
            },
        },
    }
    return df


def sloped_cheese(namespace="minecraft:overworld"):
    """Replacement for the vanilla overworld cheese with the mod's shaping."""
    return {
        "type": "minecraft:cache",
        "input": {
            "type": "minecraft:add",
            "left": {
                "type": "minecraft:mul",
                "left": {
                    "type": "minecraft:quarter_negative",
                    "input": {
                        "type": "minecraft:mul",
                        "left": {
                            "type": "minecraft:add",
                            "left": "%s/depth" % namespace,
                            "right": {
                                "type": "minecraft:cache",
                                "input": {
                                    "type": "minecraft:mul",
                                    "left": "%s/jaggedness" % namespace,
                                    "right": {
                                        "type": "minecraft:half_negative",
                                        "input": {
                                            "type": "minecraft:noise",
                                            "noise": "minecraft:jagged",
                                            "xz_scale": 1500.0,
                                            "y_scale": 0.0,
                                        },
                                    },
                                },
                            },
                        },
                        "right": "%s/factor" % namespace,
                    },
                },
                "right": 4.0,
            },
            "right": {
                "type": "minecraft:add",
                "left": "minecraft:overworld/base_3d_noise",
                "right": "terrainrefreshed:terrain_features",
            },
        },
    }


# ------------------------------------------------------------------- features
def feature_json(tree):
    return {
        "type": "terrainrefreshed:fancy_tree",
        "trunk": {"id": tree["log"], "properties": {"axis": "y"}},
        "leaves": {
            "id": tree["leaves"],
            "properties": {"distance": "7", "persistent": "false", "waterlogged": "false"},
        },
        "form": tree["form"],
        "min_height": tree["height"][0],
        "max_height": tree["height"][1],
        "canopy_radius": tree["radius"],
        "branch_chance": tree["branch"],
    }


def stream_feature_json():
    return {
        "type": "terrainrefreshed:stream",
        "length": 14,
        "width": 2,
        "depth": 1,
        "water": {"id": "minecraft:water", "properties": {"level": "0"}},
        "bed": {"id": "minecraft:gravel"},
    }


# One entry per species. `form` is the silhouette the tree grows into (see TreeForm), the two blocks
# are what it is built from, `height` is the trunk, `radius` how far the crown reaches and `branch`
# how much of the optional limb and foliage structure the form is allowed to spend. The sapling only
# drives the placement filter that keeps a species off ground it could not grow on.
TREES = {
    "fancy_oak": {
        "form": "spreading", "log": "minecraft:oak_log", "leaves": "minecraft:oak_leaves",
        "height": (6, 10), "radius": 3, "branch": 0.75, "sapling": "minecraft:oak_sapling",
    },
    "fancy_birch": {
        "form": "spreading", "log": "minecraft:birch_log", "leaves": "minecraft:birch_leaves",
        "height": (6, 9), "radius": 3, "branch": 0.7, "sapling": "minecraft:birch_sapling",
    },
    "fancy_jungle": {
        "form": "spreading", "log": "minecraft:jungle_log", "leaves": "minecraft:jungle_leaves",
        "height": (8, 15), "radius": 4, "branch": 0.6, "sapling": "minecraft:jungle_sapling",
    },
    # a spruce cone: whorls from near the ground, each one shorter than the last
    "fancy_spruce": {
        "form": "conical", "log": "minecraft:spruce_log", "leaves": "minecraft:spruce_leaves",
        "height": (12, 20), "radius": 4, "branch": 0.8, "sapling": "minecraft:spruce_sapling",
    },
    # a pine: a long bare shaft, then a few upturned tiers under the crown
    "fancy_pine": {
        "form": "pine", "log": "minecraft:spruce_log", "leaves": "minecraft:spruce_leaves",
        "height": (14, 22), "radius": 4, "branch": 0.75, "sapling": "minecraft:spruce_sapling",
    },
    # a willow: limbs that reach out and drop curtains of leaves
    "fancy_willow": {
        "form": "weeping", "log": "minecraft:dark_oak_log", "leaves": "minecraft:dark_oak_leaves",
        "height": (8, 13), "radius": 4, "branch": 0.65, "sapling": "minecraft:dark_oak_sapling",
    },
    # a tabebuya: slim trunk, one rounded dome of pink blossom
    "fancy_tabebuya": {
        "form": "floral", "log": "minecraft:cherry_log", "leaves": "minecraft:cherry_leaves",
        "height": (7, 11), "radius": 4, "branch": 0.85, "sapling": "minecraft:cherry_sapling",
    },
    # a savanna acacia: forked trunk, flat wide disc
    "fancy_acacia": {
        "form": "umbrella", "log": "minecraft:acacia_log", "leaves": "minecraft:acacia_leaves",
        "height": (6, 9), "radius": 4, "branch": 0.8, "sapling": "minecraft:acacia_sapling",
    },
    # a cypress: foliage hugging a narrow column
    "fancy_cypress": {
        "form": "columnar", "log": "minecraft:spruce_log", "leaves": "minecraft:spruce_leaves",
        "height": (10, 16), "radius": 2, "branch": 0.85, "sapling": "minecraft:spruce_sapling",
    },
    # a baobab: a thick barrel trunk with a few stubby arms
    "fancy_baobab": {
        "form": "baobab", "log": "minecraft:acacia_log", "leaves": "minecraft:acacia_leaves",
        "height": (6, 9), "radius": 3, "branch": 0.7, "sapling": "minecraft:acacia_sapling",
    },
    # a palm: a leaning shaft with nothing but fronds at the top
    "fancy_palm": {
        "form": "palm", "log": "minecraft:jungle_log", "leaves": "minecraft:jungle_leaves",
        "height": (9, 14), "radius": 3, "branch": 0.8, "sapling": "minecraft:jungle_sapling",
    },
}


# ------------------------------------------------------------------ generation
def main():
    report = allocate_cells(BIOMES, read_shelves())

    # biomes
    for b in BIOMES:
        write_json(os.path.join(DATA, MOD, "worldgen", "biome", b["id"] + ".json"), biome_json(b))

    # densities / noises
    for name, doc in density_functions().items():
        write_json(os.path.join(DATA, MOD, "worldgen", "density_function", name + ".json"), doc)
    for name, doc in NOISES.items():
        write_json(os.path.join(DATA, MOD, "worldgen", "noise", name + ".json"), doc)

    # terrain shaping: replaces the vanilla overworld cheese so every normal
    # world picks up the new terrain without any extra configuration.
    write_json(
        os.path.join(DATA, "minecraft", "worldgen", "density_function", "overworld", "sloped_cheese.json"),
        sloped_cheese(),
    )
    write_json(
        os.path.join(DATA, "minecraft", "worldgen", "density_function", "overworld_amplified", "sloped_cheese.json"),
        sloped_cheese("minecraft:overworld_amplified"),
    )
    write_json(
        os.path.join(DATA, "minecraft", "worldgen", "density_function", "overworld_large_biomes", "sloped_cheese.json"),
        sloped_cheese("minecraft:overworld_large_biomes"),
    )

    # custom features
    for name, tree in TREES.items():
        write_json(os.path.join(DATA, MOD, "worldgen", "feature", name + ".json"), feature_json(tree))
    write_json(os.path.join(DATA, MOD, "worldgen", "feature", "stream.json"), stream_feature_json())

    # placed features
    for name, tree in TREES.items():
        write_json(
            os.path.join(DATA, MOD, "worldgen", "placed_feature", name + ".json"),
            {
                "feature": "terrainrefreshed:" + name,
                "placement": [
                    {"type": "minecraft:count", "count": 1},
                    {"type": "minecraft:in_square"},
                    {"type": "minecraft:surface_water_depth_filter", "max_water_depth": 0},
                    {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR"},
                    {
                        "type": "minecraft:block_predicate_filter",
                        "predicate": {
                            "type": "minecraft:would_survive",
                            "state": tree["sapling"],
                        },
                    },
                ],
            },
        )
    write_json(
        os.path.join(DATA, MOD, "worldgen", "placed_feature", "fancy_oak_sparse.json"),
        {
            "feature": "terrainrefreshed:fancy_oak",
            "placement": [
                {"type": "minecraft:count", "count": 3},
                {"type": "minecraft:in_square"},
                {"type": "minecraft:surface_water_depth_filter", "max_water_depth": 0},
                {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR"},
                {
                    "type": "minecraft:block_predicate_filter",
                    "predicate": {"type": "minecraft:would_survive", "state": "minecraft:oak_sapling"},
                },
            ],
        },
    )
    write_json(
        os.path.join(DATA, MOD, "worldgen", "placed_feature", "stream.json"),
        {
            "feature": "terrainrefreshed:stream",
            "placement": [
                {"type": "minecraft:rarity_filter", "chance": 6},
                {"type": "minecraft:count", "count": 1},
                {"type": "minecraft:in_square"},
                {"type": "minecraft:heightmap", "heightmap": "WORLD_SURFACE_WG"},
            ],
        },
    )

    # lang
    lang = {"biome.%s.%s" % (MOD, b["id"]): b["name"] for b in BIOMES}
    write_json(os.path.join(ROOT, "src", "main", "resources", "assets", MOD, "lang", "en_us.json"), lang)

    # java climate table
    write_java_table()
    print(
        "generated %d biomes in %d vanilla neighbourhoods"
        % (len(BIOMES), len({key for _, key, _ in report}))
    )


def write_java_table():
    lines = []
    lines.append("package net.revskymc.terrainrefreshed.worldgen;")
    lines.append("")
    lines.append("import net.minecraft.core.registries.Registries;")
    lines.append("import net.minecraft.resources.Identifier;")
    lines.append("import net.minecraft.resources.ResourceKey;")
    lines.append("import net.minecraft.world.level.biome.Biome;")
    lines.append("import net.minecraft.world.level.biome.Climate;")
    lines.append("")
    lines.append("/** Climate cells owned by the Terrain Refreshed biomes. Generated by tools/generate_content.py. */")
    lines.append("public final class BiomeClimateTable {")
    lines.append("\tpublic record Entry(")
    lines.append("\t\tResourceKey<Biome> biome,")
    lines.append("\t\tClimate.Parameter temperature,")
    lines.append("\t\tClimate.Parameter humidity,")
    lines.append("\t\tClimate.Parameter continentalness,")
    lines.append("\t\tClimate.Parameter erosion,")
    lines.append("\t\tClimate.Parameter weirdness")
    lines.append("\t) {}")
    lines.append("")
    lines.append("\tprivate static final Entry[] ENTRIES = {")
    for b in BIOMES:
        params = [
            "\t\t\tClimate.Parameter.span(%sF, %sF)" % (fmt(low / 10000.0), fmt(high / 10000.0))
            for low, high in b["cell"]
        ]
        lines.append("\t\tnew Entry(")
        lines.append("\t\t\tResourceKey.create(Registries.BIOME, Identifier.fromNamespaceAndPath(\"%s\", \"%s\"))," % (MOD, b["id"]))
        for index, param in enumerate(params):
            lines.append(param + ("," if index + 1 < len(params) else ""))
        lines.append("\t\t),")
    lines.append("\t};")
    lines.append("")
    lines.append("\tprivate BiomeClimateTable() {}")
    lines.append("")
    lines.append("\tpublic static Entry[] entries() {")
    lines.append("\t\treturn ENTRIES;")
    lines.append("\t}")
    lines.append("}")
    path = os.path.join(ROOT, "src", "main", "java", "net", "revskymc", "terrainrefreshed", "worldgen", "BiomeClimateTable.java")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
