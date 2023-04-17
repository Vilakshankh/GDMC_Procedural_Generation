from noise.rng import RNG
from noise.random import randrange
from gdpc import Editor, Block
from gdpc.vector_tools import Rect, ivec2, distance, ivec3
from gdpc import WorldSlice
from structures.directions import north, east, west, south, get_ivec2, directions, left, right, to_text, ivec2_to_dir, get_ivec3, cardinal, opposite, ivec3_to_dir
from utils.geometry import get_neighbours_in_set, is_straight_ivec2, is_point_surrounded_dict, is_straight_not_diagonal_ivec2
from utils.misc import is_water
from structures.nbt.build_nbt import build_nbt
from structures.nbt.nbt_asset import NBTAsset
from structures.transformation import Transformation

def find_wall_neighbour(current : ivec2, wall_dict : dict, ordered_wall_dict : dict):
    for check in [ivec2(-1,0),ivec2(0,-1),ivec2(-1,-1),ivec2(-1,1),ivec2(1,-1),ivec2(1,0),ivec2(0,1),ivec2(1,1)]: #prefers to go right
        if current == None: #error case
            return None 
        next_wall_point = current + check
        if ordered_wall_dict.get(next_wall_point) != True and wall_dict.get(next_wall_point) == True:
            return next_wall_point

#orders the list of wall points based off the first point in the list
def order_wall_points(wall_points: list[ivec2], wall_dict: dict) -> list[ivec2]:
    ordered_wall_points: list[ivec2] = []
    ordered_wall_dict: dict() = {}
    reverse_checked = False

    ordered_wall_points.append(wall_points[0])
    ordered_wall_dict[wall_points[0]] = True
    current_wall_point = ordered_wall_points[0]
    while len(ordered_wall_points) != len(wall_points):
        next_wall_point = find_wall_neighbour(current_wall_point, wall_dict, ordered_wall_dict)
        if next_wall_point == None: #error case, clean stopping
            if reverse_checked == False: #after the first error, we reverse list and check the other way
                print("reverse")
                reverse_checked = True
                ordered_wall_points.reverse()
                current_wall_point = ordered_wall_points[-1]
            else:
                print('failed')
                break
        else:
            #print(next_wall_point)
            ordered_wall_points.append(next_wall_point)
            ordered_wall_dict[next_wall_point] = True
            current_wall_point = next_wall_point

    return ordered_wall_points

#currently not in use, adapt this function to point to the appropriate further build wall likely in the future
def build_wall(wall_points: list[ivec2], wall_dict: dict, editor : Editor, world_slice : WorldSlice, rng : RNG, wall_type : str):
    if wall_type == 'palisade':
        build_wall_palisade(wall_points, editor, world_slice, rng)
    elif wall_type == 'standard':
        build_wall_standard(wall_points, wall_dict, editor, world_slice, rng)

def build_wall_palisade(wall_points: list[ivec2], editor : Editor, world_slice : WorldSlice, water_map : dict, rng : RNG):
    #TODO cleanup the wall_points here to match the format mostly in the other build wall functions, then readress the build gate and can make it cleaner
    new_wall_points = []
    height_map = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES']
    #enhancing the wall_points list by adding height
    height = randrange(rng.value(), 4, 7)
    for vec in wall_points:
        point = [vec.x,height_map[vec.x][vec.y],vec.y]
        point+=[height]
        new_wall_points.append(point)
        # ensuring next wall piece is a different height
        next_height = randrange(rng.value(), 4, 7)
        while (height == next_height):
            next_height = randrange(rng.value(), 4, 7)
        height = next_height

    #sorting by height, so lowest sections get built first
    unordered_wall_points = new_wall_points# keep a copy of the list not sorted by height
    #new_wall_points.sort(key = lambda a: a[3])

    for point in new_wall_points:
        if water_map[point[0]][point[2]] == False:
            for y in range(point[1], point[1] + point[3]):
                #interface.placeBlock(point[0],y,point[2], 'minecraft:stone_bricks')
            #interface.placeBlock(point[0],point[1] + point[3], point[2], 'minecraft:stone_brick_wall')
                editor.placeBlock((point[0],y,point[2]), Block('minecraft:oak_log'))
            editor.placeBlock((point[0],point[1] + point[3], point[2]), Block('minecraft:oak_fence'))

    add_gates(unordered_wall_points, editor, world_slice, True, None, True)


def build_wall_standard(wall_points: list[ivec2], wall_dict : dict, inner_points: list[ivec2], editor : Editor, world_slice : WorldSlice, water_map : dict):

    wall_points = add_wall_points_height(wall_points, wall_dict, world_slice)
    wall_points = add_wall_points_directionality(wall_points, wall_dict, inner_points)
    wall_points = check_water(wall_points, water_map)
    height_map = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES']

    previous_dir = north

    walkway_list = [] #idea is to get this list and then get the new inner points of hte wall, how do I get height to those
    walkway_dict: dict() = {}


    for i,wall_point in enumerate(wall_points):
        point = wall_point[0]
        if wall_point[2] == 'water':
            continue
        else:
            if wall_point[2] == 'water_wall': 
                fill_water(ivec2(point.x, point.z), editor, height_map, world_slice)

            for y in range(height_map[point.x, point.z], point.y + 1):
                editor.placeBlock((point.x,y,point.z), Block('minecraft:stone_bricks'))
            if len(wall_point[1]) != 0:
                previous_dir = wall_point[1][0]
            editor.placeBlock((point.x,point.y + 1, point.z), Block(f'minecraft:stone_brick_stairs[facing={to_text(right[previous_dir])}]'))
            for dir in wall_point[1]:
                height_modifier = 0 #used in one case to alter height of walkway
                if i != 0 and i != len(wall_points) - 1:
                    prev_h = wall_points[i-1][0].y
                    next_h = wall_points[i+1][0].y
                    h = point.y
                    if prev_h == h - 1 and next_h == h - 1:
                        height_modifier = -1
                if right[dir] in wall_point[1]: # add corner bits for walkway
                    for new_pt in (point + get_ivec3(dir) + get_ivec3(right[dir]), point + get_ivec3(dir) + get_ivec3(right[dir]) * 2,point + get_ivec3(dir) *2 + get_ivec3(right[dir])):
                        if wall_dict.get(ivec2(new_pt.x, new_pt.z)) == True:
                            break
                        if walkway_dict.get(ivec2(new_pt.x, new_pt.z)) == None:
                            walkway_list.append(ivec2(new_pt.x, new_pt.z))
                            walkway_dict[ivec2(new_pt.x, new_pt.z)] = new_pt.y + height_modifier
                for x in range(1, 4):
                    new_pt = point + get_ivec3(dir) * x
                    if wall_dict.get(ivec2(new_pt.x, new_pt.z)) == True:
                        break
                    if walkway_dict.get(ivec2(new_pt.x, new_pt.z)) == None:
                        walkway_list.append(ivec2(new_pt.x, new_pt.z))
                        walkway_dict[ivec2(new_pt.x, new_pt.z)] = new_pt.y + height_modifier

    flatten_walkway(walkway_list, walkway_dict, editor)

    add_gates(wall_points, editor, world_slice, True, None)


def build_wall_standard_with_inner(wall_points: list[ivec2], wall_dict : dict, inner_points: list[ivec2], editor : Editor, world_slice : WorldSlice, water_map : dict, rng : RNG):

    wall_points = add_wall_points_height(wall_points, wall_dict, world_slice)
    wall_points = add_wall_points_directionality(wall_points, wall_dict, inner_points)
    wall_points = check_water(wall_points, water_map)
    height_map = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES']

    previous_dir = north

    walkway_list = [] #idea is to get this list and then get the new inner points of hte wall, how do I get height to those
    walkway_dict: dict() = {}

    inner_wall_list = []
    inner_wall_dict: dict() = {}

    for i,wall_point in enumerate(wall_points):
        point = wall_point[0]
        fill_in = False
        if wall_point[2] == 'water':
            continue
        else:
            #check if need to fill in this wall slice
            if i == 0 or i == len(wall_points)-1 or wall_points[i+1][2] == 'water' or wall_points[i-1][2] == 'water' or point.y > wall_points[i-1][0].y+4 or point.y > wall_points[i+1][0].y+4:
                fill_in = True

            elif wall_point[2] == 'water_wall': #not in current use, perhaps future
                fill_water(ivec2(point.x, point.z), editor, height_map, world_slice)

            for y in range(height_map[point.x, point.z], point.y + 1):
                editor.placeBlock((point.x,y,point.z), Block('minecraft:stone_bricks'))
            if len(wall_point[1]) != 0:
                previous_dir = wall_point[1][0]
            editor.placeBlock((point.x,point.y + 1, point.z), Block(f'minecraft:stone_brick_stairs[facing={to_text(right[previous_dir])}]'))
            for dir in wall_point[1]:
                height_modifier = 0 #used in one case to alter height of walkway
                if i != 0 and i != len(wall_points) - 1:
                    prev_h = wall_points[i-1][0].y
                    next_h = wall_points[i+1][0].y
                    h = point.y
                    if prev_h == h - 1 and next_h == h - 1:
                        height_modifier = -1
                if right[dir] in wall_point[1]: # add corner bits for walkway
                    for new_pt in (point + get_ivec3(dir) + get_ivec3(right[dir]), point + get_ivec3(dir) + get_ivec3(right[dir]) * 2,point + get_ivec3(dir) *2 + get_ivec3(right[dir])):
                        if wall_dict.get(ivec2(new_pt.x, new_pt.z)) == True:
                            break
                        if walkway_dict.get(ivec2(new_pt.x, new_pt.z)) == None:
                            walkway_list.append(ivec2(new_pt.x, new_pt.z))
                            walkway_dict[ivec2(new_pt.x, new_pt.z)] = new_pt.y + height_modifier
                        if fill_in:
                            for y in range(height_map[new_pt.x, new_pt.z], point.y):
                                editor.placeBlock((new_pt.x,y,new_pt.z), Block('minecraft:stone_bricks'))
                            if water_map[new_pt.x][new_pt.z] == True:
                                fill_water(ivec2(new_pt.x, new_pt.z), editor, height_map, world_slice)
                        
                    #inner wall
                    for wall_pt in (point + get_ivec3(dir)*2 + get_ivec3(right[dir])*2, point + get_ivec3(dir) + get_ivec3(right[dir]) * 3,point + get_ivec3(dir) *3 + get_ivec3(right[dir])):
                        if wall_dict.get(ivec2(wall_pt.x, wall_pt.z)) != True and walkway_dict.get(ivec2(wall_pt.x, wall_pt.z)) == None:
                            inner_wall_list.append(ivec3(wall_pt.x,point.y,wall_pt.z))
                for x in range(1, 4):
                    new_pt = point + get_ivec3(dir) * x
                    if wall_dict.get(ivec2(new_pt.x, new_pt.z)) == True:
                        break
                    if walkway_dict.get(ivec2(new_pt.x, new_pt.z)) == None:
                        walkway_list.append(ivec2(new_pt.x, new_pt.z))
                        walkway_dict[ivec2(new_pt.x, new_pt.z)] = new_pt.y + height_modifier
                        #inner wall
                        if x == 3:
                            wall_pt = point + get_ivec3(dir) * 4
                            if wall_dict.get(ivec2(wall_pt.x, wall_pt.z)) != True and walkway_dict.get(ivec2(wall_pt.x, wall_pt.z)) == None:
                                inner_wall_list.append(ivec3(wall_pt.x,point.y,wall_pt.z))
                    if fill_in:
                        for y in range(height_map[new_pt.x, new_pt.z], point.y):
                            editor.placeBlock((new_pt.x,y,new_pt.z), Block('minecraft:stone_bricks'))
                        if water_map[new_pt.x][new_pt.z] == True:
                            fill_water(ivec2(new_pt.x, new_pt.z), editor, height_map, world_slice)
                        

    for pt in inner_wall_list:
        if walkway_dict.get(ivec2(pt.x, pt.z)) == None: #check again since walkway was not completed as inner wall was being added
            inner_wall_dict[ivec2(pt.x, pt.z)] = True #can put something else here if needed
            for y in range(height_map[pt.x, pt.z], pt.y + 1):
                editor.placeBlock((pt.x,y,pt.z), Block('minecraft:stone_bricks'))
            if water_map[pt.x][pt.z] == True: #behaviour is to place inner wall into water til floor
                fill_water(ivec2(pt.x, pt.z), editor, height_map, world_slice)


    walkway_dict = flatten_walkway(walkway_list, walkway_dict, editor)
    add_towers(walkway_list, walkway_dict, editor, rng)
    add_gates(wall_points, editor, world_slice, False, inner_wall_dict)

#adds direction to the wall points to know which way we need to build walkways
def add_wall_points_directionality(wall_points : list[ivec3], wall_dict : dict, inner_points : list[ivec2]):
    enhanced_wall_points = []
    for point in wall_points:  
        enhanced_point = [point, [], None]
        ivec2_point = ivec2(point.x,point.z)
        neighbours = get_neighbours_in_set(ivec2_point, inner_points)
        for neighbour in neighbours:
            if wall_dict.get(neighbour) != True:
                enhanced_point[1].append(ivec2_to_dir(neighbour - ivec2_point))

        enhanced_wall_points.append(enhanced_point)

    return enhanced_wall_points

WALL_HEIGHT = 10 #max height of wall
def add_wall_points_height(wall_points : list[ivec2], world_slice : WorldSlice):

    height_wall_points = []
    height_map = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES']
    current_height = height_map[wall_points[0].x,wall_points[0].y]
    target_height = current_height
    for i,point in enumerate(wall_points):
        if i %5 == 0:
            if len(wall_points)-1 < i+5:
                target_height = height_map[wall_points[0].x,wall_points[0].y] #wrap around a bit
            else:
                target_height = height_map[wall_points[i+5].x,wall_points[i+5].y]
            if target_height > current_height + (WALL_HEIGHT * 2/3) or target_height < current_height + (WALL_HEIGHT * 2/3): #deal with small height anomalies by looking for a point a bit further
                if len(wall_points)-1 < i+10:
                    target_height = height_map[wall_points[0].x,wall_points[0].y] #wrap around a bit
                else:
                    target_height = height_map[wall_points[i+10].x,wall_points[i+10].y]
        #add a check to see for drastic height difference
        if current_height < height_map[wall_points[i].x,wall_points[i].y] - WALL_HEIGHT *2/3:
            current_height = height_map[wall_points[i].x,wall_points[i].y]
            target_height = current_height
        elif current_height != target_height and ( 1 < i < len(wall_points)-2):
            if is_straight_ivec2(wall_points[i-2], wall_points[i+2], 4):
                if current_height < target_height:
                    current_height += 1
                elif current_height > target_height:
                    current_height -= 1
        new_point = ivec3(point.x, current_height + WALL_HEIGHT,point.y)
        height_wall_points.append(new_point)

    return height_wall_points

RANGE = 3 #range for walkway flattening
NEIGHBOURS = [(x, z) for x in range(-RANGE, RANGE + 1) for z in range(-RANGE, RANGE + 1)]

def flatten_walkway(walkway_list : list[ivec2], walkway_dict : dict, editor : Editor):

    for point in walkway_list:
        walkway_dict[point] = (average_neighbour_height(point.x, point.y, walkway_dict))

    #first pass places slabs and changes dict heights
    for key in walkway_dict:
        height = walkway_dict[key]
        if height % 1 <= 0.25:
            editor.placeBlock((key.x,round(height),key.y), Block('minecraft:oak_slab'))
            walkway_dict[key] = round(height)
        elif 0.25 < height % 1 <= 0.5:
            editor.placeBlock((key.x,round(height),key.y), Block('minecraft:oak_slab[type=top]'))
            walkway_dict[key] = round(height)+0.49
        elif 0.5 < height % 1 <= 0.75:
            editor.placeBlock((key.x,round(height)-1,key.y), Block('minecraft:oak_slab[type=top]'))
            walkway_dict[key] = round(height)-0.51
        else:
            editor.placeBlock((key.x,round(height),key.y), Block('minecraft:oak_slab'))
            walkway_dict[key] = round(height)

    #2nd pass to add stairs based on first pass changes
    for key in walkway_dict:
        height = walkway_dict[key]
        for direction in cardinal:
            delta = get_ivec2(direction)
            neighbour = key + delta
            if walkway_dict.get(neighbour) == None:
                continue
            elif height % 1 ==0: # bottom slab
                if walkway_dict.get(neighbour) - height >= 1:
                    editor.placeBlock((key.x,round(height), key.y), Block(f'minecraft:oak_stairs[facing={to_text(direction)}]'))
            else: #top slab
                if walkway_dict.get(neighbour) - height <= -1:
                    editor.placeBlock((key.x,round(height), key.y), Block(f'minecraft:oak_stairs[facing={to_text(opposite(direction))}]'))

    return walkway_dict

def average_neighbour_height(x : int, z : int, walkway_dict : dict) -> int:
    height_sum = 0
    total_weight = 0

    for dx, dz in NEIGHBOURS:
        if ivec2(x + dx, z + dz) not in walkway_dict: # we only need to flatten for within a district
            continue
        elif abs(walkway_dict[ivec2(x + dx, z + dz)] - walkway_dict[ivec2(x,z)]) >= 4: #ignore extremes
            continue

        distance = abs(dx) + abs(dz)
        weight = 0.8 ** distance
        height = walkway_dict[ivec2(x + dx,z + dz)]
        height_sum += height * weight
        total_weight += weight

    return (height_sum / total_weight)

WATER_CHECK = 5 #the water the distance the wall will build across
#water checking
def check_water(wall_points : list, water_map : dict):
    buildable = False #bool, if true, set to water_wall, water otherwise
    long_water = True #assume water start
    for i,wall_pt in enumerate(wall_points):
        point = wall_pt[0]

        if water_map[point.x][point.z] == True:
        # more complex attempt at having wall be able to bridge some water, implement better later
            if long_water:
                wall_points[i][2] = 'water'
            elif buildable:
                wall_points[i][2] = 'water_wall'

            else: #check if can bridge
                wall_points[i][2] = 'water' #default
                for a in range(1,WATER_CHECK+1):
                    if a+i>=len(wall_points): #OUT OF BOUNDS
                        break
                    pt = wall_points[a+i][0]
                    if water_map[pt.x][pt.z] == False: #found land within range
                        buildable = True
                        long_water = False
                        wall_points[i][2] = 'water_wall'
                        break
                    elif a == WATER_CHECK:
                        long_water = True
        elif water_map[point.x][point.z] == False:
            buildable = False #reset buildability
            long_water = False

    return wall_points

def fill_water(pt : ivec2, editor : Editor, height_map : dict, world_slice : WorldSlice):
    height = height_map[pt.x, pt.y] - 1
    while is_water(ivec3(pt.x, height, pt.y), world_slice) and height != 0:
        editor.placeBlock((pt.x,height,pt.y), Block('minecraft:mossy_stone_bricks'))
        height = height - 1

def add_towers(walkway_list : list[ivec2], walkway_dict : dict, editor : Editor, rng : RNG):
    distance_to_next_tower = 80 #minimum
    tower_possible = randrange(rng.value(), 0, distance_to_next_tower/2) #counter if 0, allow a tower to be built
    tower = NBTAsset.construct(
        name     = 'tower',
        type     = 'tower',
        filepath = 'assets/city_wall/towers/basic_tower.nbt',
        origin   = (3, 1, 3),
        palette = None
    )
    
    for point in walkway_list:
        if tower_possible == 0:
            #print("tower possible")
            if is_point_surrounded_dict(point, walkway_dict):
                tower_possible = distance_to_next_tower
                #prep tower base
                neighbours = [ivec2(x, z) for x in range(point.x -2, point.x + 3) for z in range(point.y -2, point.y + 3)]
                point_height = round(walkway_dict.get(point))
                for neighbour in neighbours:
                    for height in range(point_height - 1, point_height + 6):
                        if height == point_height + 5 or walkway_dict.get(neighbour) == None:
                            editor.placeBlock((neighbour.x,height,neighbour.y), Block('minecraft:stone_bricks'))

                #build tower
                build_nbt(
                    editor = editor, 
                    asset = tower,
                    transformation=Transformation(
                        offset=ivec3(point.x, point_height+6,point.y),
                        mirror=(True, False, False),
                        #diagonal_mirror=True,
                    ),
                )
            #else:
            #    print("actually it isnt")
        else:
            tower_possible -=1

def add_gates(wall_list : list, editor : Editor, world_slice : WorldSlice, is_thin : bool, inner_wall_dict : dict, palisade : bool = False):
    distance_to_next_gate = 30 #minimum
    gate_possible = 0 #counter if 0, allow a tower to be built
    height_map = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES']

    basic_wide_gate = NBTAsset.construct(
        name     = 'gate',
        type     = 'gate',
        filepath = 'assets/city_wall/gates/basic_wide_gate.nbt',
        origin   = (3, 1, 3),
        palette = None
    )

    basic_thin_gate = NBTAsset.construct(
        name     = 'gate',
        type     = 'gate',
        filepath = 'assets/city_wall/gates/basic_thin_gate.nbt',
        origin   = (1, 1, 3),
        palette = None
    )

    basic_palisade_gate = NBTAsset.construct(
        name     = 'gate',
        type     = 'gate',
        filepath = 'assets/city_wall/gates/basic_palisade_gate.nbt',
        origin   = (1, 1, 2),
        palette = None
    )

    for i,wall_point in enumerate(wall_list):
        if palisade:
            point = ivec3(wall_point[0], wall_point[1], wall_point[2])
            if gate_possible == 0:
                if i<len(wall_list) - 7 and is_straight_not_diagonal_ivec2(ivec2(point.x,point.z), ivec2(wall_list[i+6][0], wall_list[i+6][2]), 6) and abs(point.y - wall_list[i+6][1]) <= 1:

                    middle_point = ivec3(wall_list[i+2][0],wall_list[i+2][1],wall_list[i+2][2]) 
                    if point.x == wall_list[i+6][0]:
                        dir = east
                    else:
                        dir = north
                    if dir in (north, south):
                        neighbours = [ivec2(x, z) for x in range(middle_point.x -2, middle_point.x + 3) for z in range(middle_point.z -1, middle_point.z + 2)]
                    else: 
                        neighbours = [ivec2(x, z) for x in range(middle_point.x -1, middle_point.x + 2) for z in range(middle_point.z -2, middle_point.z + 3)]
                    height = height_map[middle_point.x, middle_point.z]
                    gate_possible = distance_to_next_gate
                    for height in range(height, height + 10):
                        for neighbour in neighbours:
                            editor.placeBlock((neighbour.x,height,neighbour.y), Block('minecraft:air'))
                    #build gate
                    diagonal_mirror = False
                    if dir in (north, south):
                        diagonal_mirror = True

                    build_nbt(
                        editor = editor, 
                        asset = basic_palisade_gate,
                        transformation=Transformation(
                            offset=ivec3(middle_point.x, height_map[middle_point.x, middle_point.z],middle_point.z),
                            mirror=(True, False, False),
                            diagonal_mirror=diagonal_mirror,
                        ),
                    )
            else:
                gate_possible -=1
        else:
            point = wall_point[0]
            if gate_possible == 0:
                if i<len(wall_list) - 7 and is_straight_not_diagonal_ivec2(ivec2(point.x,point.z), ivec2(wall_list[i+6][0].x, wall_list[i+6][0].z), 6) and abs(point.y - wall_list[i+6][0].y) <= 1:
                    if is_thin:
                        middle_point = wall_list[i+3][0]
                        dir = get_ivec3(wall_list[i+3][1][0])
                        if ivec3_to_dir(dir) in (north, south):
                            neighbours = [ivec2(x, z) for x in range(middle_point.x -3, middle_point.x + 4) for z in range(middle_point.z -1, middle_point.z + 2)]
                        else: 
                            neighbours = [ivec2(x, z) for x in range(middle_point.x -1, middle_point.x + 2) for z in range(middle_point.z -3, middle_point.z + 4)]
                        height = height_map[middle_point.x, middle_point.z]
                        gate_possible = distance_to_next_gate
                        for height in range(height, height + 6):
                            for neighbour in neighbours:
                                editor.placeBlock((neighbour.x,height,neighbour.y), Block('minecraft:air'))
                        #build gate
                        diagonal_mirror = False
                        if ivec3_to_dir(dir) in (north, south):
                            diagonal_mirror = True

                        build_nbt(
                            editor = editor, 
                            asset = basic_thin_gate,
                            transformation=Transformation(
                                offset=ivec3(middle_point.x, height_map[middle_point.x, middle_point.z],middle_point.z),
                                mirror=(True, False, False),
                                diagonal_mirror=diagonal_mirror,
                            ),
                        )
                    else:
                        dir = get_ivec3(wall_list[i+3][1][0])
                        middle_point = wall_list[i+3][0] + dir * 2
                        #checking inner wall, if it is not where it is expected to be, not a valid gate location
                        
                        for a in range(i, i+7):
                            inner_wall_pt = wall_list[a][0] + dir * 4
                            if inner_wall_dict.get(ivec2(inner_wall_pt.x, inner_wall_pt.z)) == None:
                                break
                            #prep gate
                            if a == i+6:
                                neighbours = [ivec2(x, z) for x in range(middle_point.x -3, middle_point.x + 4) for z in range(middle_point.z -3, middle_point.z + 4)]
                                height = height_map[middle_point.x, middle_point.z]
                                gate_possible = distance_to_next_gate
                                for height in range(height, height + 6):
                                    for neighbour in neighbours:
                                        editor.placeBlock((neighbour.x,height,neighbour.y), Block('minecraft:air'))

                                #build gate
                                diagonal_mirror = False
                                if ivec3_to_dir(dir) in (north, south):
                                    diagonal_mirror = True
                                build_nbt(
                                    editor = editor, 
                                    asset = basic_wide_gate,
                                    transformation=Transformation(
                                        offset=ivec3(middle_point.x, height_map[middle_point.x, middle_point.z],middle_point.z),
                                        mirror=(True, False, False),
                                        diagonal_mirror=diagonal_mirror,
                                    ),
                                )
            else:
                gate_possible -=1