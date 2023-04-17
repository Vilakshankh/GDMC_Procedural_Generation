from gdpc.vector_tools import ivec3, distance
from gdpc import WorldSlice, Editor
from structures.directions import all_8, vector
from paths.a_star import a_star, COUNTER_LIMIT_EXCEEDED
from utils.bounds import is_in_bounds

HEURISTIC_WEIGHT = 3

def fill_out_highway(points : list[ivec3]) -> list[ivec3]:
    full_points = []

    point_a = points.pop()
    
    full_points.append(point_a)
    
    while len(points) > 0:
        point_b = points.pop()

        full_points += find_in_betweeners(point_a, point_b)
        full_points.append(point_a)

        point_a = point_b

    return full_points

def find_in_betweeners(point_a : ivec3, point_b : ivec3) -> list[ivec3]:
    diff_vec = ivec3(0, 0, 0)
    magnitude = 2
    points = []

    if point_a.x + 2 == point_b.x:
        diff_vec += ivec3(1, 0, 0)
    elif point_a.x + 4 == point_b.x:
        diff_vec += ivec3(1, 0, 0)
        magnitude = 4

    if point_a.z + 2 == point_b.z:
        diff_vec += ivec3(0, 0, 1)
    elif point_a.z + 4 == point_b.z:
        diff_vec += ivec3(0, 0, 1)
        magnitude = 4

    if point_a.x - 2 == point_b.x:
        diff_vec += ivec3(-1, 0, 0)
    elif point_a.x - 4 == point_b.x:
        diff_vec += ivec3(-1, 0, 0)
        magnitude = 4

    if point_a.z - 2 == point_b.z:
        diff_vec += ivec3(0, 0, -1)
    elif point_a.z - 4 == point_b.z:
        diff_vec += ivec3(0, 0, -1)
        magnitude = 4
    
    for i in range(1, magnitude):
        pt = point_a + i * diff_vec

        pt.y = (point_a.y * (magnitude - i) + point_b.y * i) // magnitude

        points.append(pt)

    return points


def route_highway(start : ivec3, end : ivec3, world_slice : WorldSlice, water_map : list[list[bool]], editor : Editor) -> list[ivec3]:
    
    def get_cost(prev_cost : int, path : list[ivec3]):
        if len(path) == 1:
            return 2 * distance(path[-1], end)
        
        last = path[-1]

        prev_heuristic = HEURISTIC_WEIGHT * distance(path[-2], end)

        path_cost = prev_cost - prev_heuristic
        base_length_cost = 2 # added as length of path increases

        height_diff = abs(last.y - world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES'][last.x][last.z])
        height_cost = height_diff * 5

        if water_map[last.x][last.z]:
            base_length_cost += 30 # WATER COST. Making this big means water gets avoided when possible.

        y_diff_penalty = abs(path[-1].y - path[-2].y) * 2

        return path_cost + height_cost + base_length_cost + y_diff_penalty + distance(path[-2], last) + HEURISTIC_WEIGHT * distance(last, end)
    
    # prefer 4 out neighbours, but will accept 2 out
    def get_neighbours(point : ivec3):
        neighbours = []
        
        for direction in all_8:
            direction_vector = vector(direction)

            # First consider 4 out
            neighbour = point + direction_vector * 4

            if is_in_bounds(neighbour, world_slice):
                actual_neighbour_y = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES'][neighbour.x][neighbour.z]
                
                if point.y < actual_neighbour_y - 2:
                    neighbour.y = point.y + 2
                elif point.y > actual_neighbour_y + 2:
                    neighbour.y = point.y - 2
                else:
                    neighbour.y = actual_neighbour_y

                if abs(point.y - neighbour.y) <= 2:
                    neighbours.append(neighbour)
                    continue


            # Don't consider compounds for short jumps
            if sum(direction_vector) >= 2:
                continue

            # Then consider 2 out
            neighbour = point + direction_vector * 2

            if is_in_bounds(neighbour, world_slice):
                neighbour.y = world_slice.heightmaps['MOTION_BLOCKING_NO_LEAVES'][neighbour.x][neighbour.z]

                if abs(point.y - neighbour.y) <= 2:
                    neighbours.append(neighbour)
                    continue
                
        return neighbours
    
    highway = a_star(start, end, get_neighbours, get_cost)

    if highway == COUNTER_LIMIT_EXCEEDED:
        print('Pathfinding took too long: Trying to route to the midpoint')
        midpoint = (start + end) / 2
        
        part1 = a_star(start, midpoint, get_neighbours, get_cost)
        part2 = a_star(midpoint, end, get_neighbours, get_cost)

        if part1 == COUNTER_LIMIT_EXCEEDED or part2 == COUNTER_LIMIT_EXCEEDED or part1 is None or part2 is None:
            return None

        part1.pop()
        return part1 + part2
    
    return highway