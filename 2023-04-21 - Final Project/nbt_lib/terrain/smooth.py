from districts.district import District
from gdpc import Editor, WorldSlice, Block
from gdpc.vector_tools import ivec2, ivec3
from terrain.set_height import set_height

def smooth(district : District, district_map : list[list[District]], world_slice : WorldSlice, editor : Editor, water_map : list[list[bool]]):
    print(f'Smoothing {district}')
    updated_heights = dict()

    for x, _, z in district.points:
        key = x, z

        # we don't want to flatten water tiles
        if water_map[x][z]:
            continue

        updated_heights[key] = (average_neighbour_height(x, z, world_slice))

    for key in updated_heights:
        y = updated_heights[key]
        x, z = key
        set_height(x, y, z, world_slice, editor)

RANGE = 10
NEIGHBOURS = [(x, z) for x in range(-RANGE, RANGE + 1) for z in range(-RANGE, RANGE + 1)]

def average_neighbour_height(x : int, z : int, world_slice : WorldSlice) -> int:
    height_sum = 0
    total_weight = 0

    for dx, dz in NEIGHBOURS:
        distance = abs(dx) + abs(dz)
        weight = 0.8 ** distance
        height = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES'][x + dx][z + dz]
        height_sum += height * weight
        total_weight += weight

    return round(height_sum / total_weight)

# updates the points set of a district to be correct
def update_district_points(district : District, world_slice : WorldSlice):
    district.points.clear()
    sum_point = ivec3(0, 0, 0)
    
    for x, z in district.points_2d:
        y = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES'][x][z]
        point = ivec3(x, y, z)
        district.points.add(point)
        sum_point += point