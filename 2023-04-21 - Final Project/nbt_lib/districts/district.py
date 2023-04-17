from gdpc.vector_tools import ivec2, ivec3

class District:
    id_counter = 0
    id : int
    points : set[ivec3]
    points_2d : set[ivec2]
    origin : ivec3
    sum : ivec3
    area : int
    adjacency : dict[any, int]
    edges : set[ivec3]
    adjacencies_total : int
    is_urban : bool

    def __init__(self, origin : ivec3, is_urban : bool) -> None:
        self.id = District.id_counter
        District.id_counter += 1
        
        self.origin = origin
        self.sum = ivec3(0, 0, 0)
        self.area = 1
        self.adjacency = {}
        self.points = {origin}
        self.points_2d = {(origin.x, origin.y)}
        self.edges = set()
        self.adjacencies_total = 0
        self.is_urban = is_urban

    def add_point(self, point : ivec3):
        self.points.add(point)
        self.points_2d.add(ivec2(point.x, point.z))
        self.sum += point
        self.area += 1

    def add_adjacency(self, district):
        if district not in self.adjacency:
            self.adjacency[district] = 0
        
        self.adjacencies_total += 1
        self.adjacency[district] += 1
    
    def get_adjacency(self, district):
        if district not in self.adjacency:
            return 0
        
        return self.adjacency[district]
    
    def get_adjacent_districts(self) -> list:
        return list(self.adjacency.keys())
    
    def get_adjacency_ratio(self, district) -> float:
        return float(self.get_adjacency(district)) / float(self.adjacencies_total)
    
    def __repr__(self) -> str:
        return f'district {self.id}'
    
    def average(self) -> ivec3:
        return ivec3(
            self.sum.x // self.area,
            self.sum.y // self.area,
            self.sum.z // self.area,
        )