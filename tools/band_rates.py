#!/usr/bin/env python3
"""Cross-tabulates a locate sweep against the climate band each committed cell sits in.

A cell can pass every offline check and still never appear near a search origin, because the world
noise is bell shaped and does not visit every part of climate space. The only real measurement of
that is `/locate biome` from the server, so this script joins its output to the committed climate
table and prints the hit rate per band of every axis. The windows in tools/generate_content.py
(POPULAR_WEIRDNESS, POPULAR_EROSION) are the bands whose rates say the region carries no terrain.

The table has to be the one that produced the sweep, so run this before regenerating content.

Usage: python tools/band_rates.py <locate-output-file>
"""

import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from climate_audit import NAME, TABLE, axes, to_box  # noqa: E402

AXES = ("temperature", "humidity", "continentalness", "erosion", "weirdness")
RESULT = re.compile(r"^(FOUND|MISSING) +([a-z_0-9]+)")


def read_cells():
    cells = {}
    for chunk in open(TABLE, encoding="utf-8").read().split("new Entry(")[1:]:
        cells[NAME.search(chunk).group(1)] = to_box(chunk)
    return cells


def read_results(path):
    outcomes = {}
    for line in open(path, encoding="utf-8"):
        match = RESULT.match(line)
        if match:
            outcomes[match.group(2)] = match.group(1) == "FOUND"
    return outcomes


def main():
    outcomes = read_results(sys.argv[1])
    cells = read_cells()
    if not outcomes:
        raise SystemExit("no locate results in %s" % sys.argv[1])

    measured = [name for name in cells if name in outcomes]
    print("measured %d of %d cells, %d found" % (
        len(measured), len(cells), sum(1 for name in measured if outcomes[name])))

    for axis, name in enumerate(AXES):
        bands = collections.defaultdict(lambda: [0, 0])
        for biome in measured:
            band = tuple(round(value / 10000.0, 4) for value in list(axes(cells[biome]))[axis])
            bands[band][0 if outcomes[biome] else 1] += 1
        print("\n== %s" % name)
        for band in sorted(bands):
            hit, miss = bands[band]
            print("   %-16s found=%-3d missing=%-3d rate=%.2f" % (
                "%g,%g" % band, hit, miss, hit / float(hit + miss)))


if __name__ == "__main__":
    main()
