package net.revskymc.terrainrefreshed.worldgen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.Feature;

/**
 * A meandering stream that cuts a channel into the terrain, lays a bed of gravel and fills the
 * channel with water. The channel follows the local surface height so it flows downhill instead of
 * floating over the landscape.
 */
public record StreamFeature(
	int length,
	int width,
	int depth,
	BlockState water,
	BlockState bed
) implements Feature {
	public static final MapCodec<StreamFeature> CODEC = RecordCodecBuilder.mapCodec(
		i -> i.group(
				Codec.intRange(2, 64).fieldOf("length").forGetter(StreamFeature::length),
				Codec.intRange(1, 8).fieldOf("width").forGetter(StreamFeature::width),
				Codec.intRange(1, 4).fieldOf("depth").forGetter(StreamFeature::depth),
				BlockState.FULL_CODEC.fieldOf("water").forGetter(StreamFeature::water),
				BlockState.FULL_CODEC.fieldOf("bed").forGetter(StreamFeature::bed)
			)
			.apply(i, StreamFeature::new)
	);

	private static final int PLACEMENT_FLAGS = 2;

	@Override
	public MapCodec<StreamFeature> codec() {
		return CODEC;
	}

	@Override
	public boolean place(final WorldGenLevel level, final ChunkGenerator chunkGenerator, final RandomSource random, final BlockPos origin) {
		int minX = (origin.getX() >> 4) << 4;
		int minZ = (origin.getZ() >> 4) << 4;
		Direction flow = Direction.Plane.HORIZONTAL.getRandomDirection(random);
		Direction bank = flow.getClockWise();
		int x = origin.getX();
		int z = origin.getZ();
		boolean placed = false;

		for (int step = 0; step < this.length; step++) {
			if (step > 0) {
				if (random.nextFloat() < 0.4F) {
					int drift = random.nextBoolean() ? 1 : -1;
					x += bank.getStepX() * drift;
					z += bank.getStepZ() * drift;
				}

				x += flow.getStepX();
				z += flow.getStepZ();
			}

			x = Mth.clamp(x, minX, minX + 15);
			z = Mth.clamp(z, minZ, minZ + 15);
			placed |= this.carveColumn(level, x, z, bank);
		}

		return placed;
	}

	private boolean carveColumn(final WorldGenLevel level, final int x, final int z, final Direction bank) {
		boolean placed = false;
		int half = (this.width - 1) / 2;

		for (int offset = -half; offset <= half; offset++) {
			int columnX = x + bank.getStepX() * offset;
			int columnZ = z + bank.getStepZ() * offset;
			int surface = level.getHeight(Heightmap.Types.WORLD_SURFACE_WG, columnX, columnZ);

			if (surface <= level.getMinY() + 1 || surface >= level.getMaxY() || surface <= level.getSeaLevel()) {
				continue;
			}

			BlockPos bedPos = new BlockPos(columnX, surface - this.depth, columnZ);
			level.setBlock(bedPos, this.bed, PLACEMENT_FLAGS);

			for (int i = 0; i < this.depth; i++) {
				level.setBlock(new BlockPos(columnX, surface - i, columnZ), this.water, PLACEMENT_FLAGS);
			}

			placed = true;
		}

		return placed;
	}
}
