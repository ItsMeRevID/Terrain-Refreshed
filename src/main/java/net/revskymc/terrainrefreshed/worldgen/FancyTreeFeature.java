package net.revskymc.terrainrefreshed.worldgen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.Feature;

/**
 * A tree grown by one of the {@link TreeForm} silhouettes.
 *
 * The vanilla tree feature builds a straight trunk plus a single foliage blob, which reads as a
 * stick with a pompom. This one asks its form for the logs and leaves, then only takes care of the
 * bookkeeping the game insists on: the trunk and limb blocks go down first, and every leaf keeps
 * the distance value the game computes from the real log positions, so the foliage does not decay
 * away once the tree is generated.
 */
public record FancyTreeFeature(
	BlockState trunk,
	BlockState leaves,
	TreeForm form,
	int minHeight,
	int maxHeight,
	int canopyRadius,
	float branchChance
) implements Feature {
	public static final MapCodec<FancyTreeFeature> CODEC = RecordCodecBuilder.mapCodec(
		i -> i.group(
				BlockState.FULL_CODEC.fieldOf("trunk").forGetter(FancyTreeFeature::trunk),
				BlockState.FULL_CODEC.fieldOf("leaves").forGetter(FancyTreeFeature::leaves),
				Codec.STRING.xmap(TreeForm::byName, form -> form.name().toLowerCase(Locale.ROOT))
					.fieldOf("form").forGetter(FancyTreeFeature::form),
				Codec.intRange(2, 64).fieldOf("min_height").forGetter(FancyTreeFeature::minHeight),
				Codec.intRange(2, 64).fieldOf("max_height").forGetter(FancyTreeFeature::maxHeight),
				Codec.intRange(1, 12).fieldOf("canopy_radius").forGetter(FancyTreeFeature::canopyRadius),
				Codec.floatRange(0.0F, 1.0F).fieldOf("branch_chance").forGetter(FancyTreeFeature::branchChance)
			)
			.apply(i, FancyTreeFeature::new)
	);

	private static final int MAX_LEAF_DISTANCE = 7;
	private static final int PLACEMENT_FLAGS = 2;

	@Override
	public MapCodec<FancyTreeFeature> codec() {
		return CODEC;
	}

	@Override
	public boolean place(final WorldGenLevel level, final ChunkGenerator chunkGenerator, final RandomSource random, final BlockPos origin) {
		int height = this.minHeight + (this.maxHeight > this.minHeight ? random.nextInt(this.maxHeight - this.minHeight + 1) : 0);
		int headroom = this.form.spreadsCrown() ? this.canopyRadius + 2 : 2;

		if (origin.getY() <= level.getMinY() || origin.getY() + height + headroom > level.getMaxY()) {
			return false;
		}

		Map<BlockPos, BlockState> logs = new LinkedHashMap<>();
		Map<BlockPos, BlockState> foliage = new HashMap<>();
		this.form.grow(this, random, origin, height, logs, foliage);

		Map<BlockPos, Integer> distances = this.distancesToLogs(logs.keySet(), new HashSet<>(foliage.keySet()));

		for (Map.Entry<BlockPos, BlockState> entry : logs.entrySet()) {
			level.setBlock(entry.getKey(), entry.getValue(), PLACEMENT_FLAGS);
		}

		for (Map.Entry<BlockPos, BlockState> entry : foliage.entrySet()) {
			Integer distance = distances.get(entry.getKey());

			if (distance == null || logs.containsKey(entry.getKey())) {
				continue;
			}

			BlockState state = entry.getValue();

			if (state.hasProperty(BlockStateProperties.DISTANCE)) {
				state = state.setValue(BlockStateProperties.DISTANCE, distance);
			}

			level.setBlock(entry.getKey(), state, PLACEMENT_FLAGS);
		}

		return true;
	}

	private Map<BlockPos, Integer> distancesToLogs(final Iterable<BlockPos> logs, final Set<BlockPos> foliage) {
		Map<BlockPos, Integer> distances = new HashMap<>();
		Deque<BlockPos> queue = new ArrayDeque<>();

		for (BlockPos log : logs) {
			distances.put(log, 0);
			queue.add(log);
		}

		while (!queue.isEmpty()) {
			BlockPos pos = queue.poll();
			int distance = distances.get(pos);

			if (distance >= MAX_LEAF_DISTANCE) {
				continue;
			}

			for (Direction direction : Direction.values()) {
				BlockPos neighbour = pos.relative(direction);

				if (!distances.containsKey(neighbour) && foliage.contains(neighbour)) {
					distances.put(neighbour, distance + 1);
					queue.add(neighbour);
				}
			}
		}

		return distances;
	}
}
