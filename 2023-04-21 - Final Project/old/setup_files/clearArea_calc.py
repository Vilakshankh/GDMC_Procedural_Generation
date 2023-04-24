from gdpc import __url__, Editor, Block, geometry
from gdpc.vector_tools import addY



#flattens the area with the absolute minimum height
def flatten_area(heightmap, buildRect, editor,build_area):
    min = build_area.begin[1]-1
    max = build_area.size[1]+min
    
    print("max height is: ", max)
    print("min height is: ", min)

    for x in range(buildRect._offset[0], buildRect._offset[0] + buildRect.size[0]):
        for z in range(buildRect._offset[1], buildRect._offset[1] + buildRect.size[1]):
            block=editor.getBlock((x, min, z))
            print(block.id)
            #if block.id == "air":
            editor.placeBlock((x, min, z), Block("grass_block"))
                


    print("Build area flattened!")

def clear_area(heightmap, buildRect, editor,build_area, world_slice):
    bottom = world_slice.heightmaps["MOTION_BLOCKING_NO_LEAVES"]
    top = world_slice.heightmaps["WORLD_SURFACE"]
    
    for x in range(buildRect._offset[0], buildRect._offset[0] + buildRect.size[0]):
        for z in range(buildRect._offset[1], buildRect._offset[1] + buildRect.size[1]):
            start = bottom[(x - buildRect._offset[0], z - buildRect._offset[1])]
            end = top[(x - buildRect._offset[0], z - buildRect._offset[1])]
            block = editor.getBlock((x, start - 1, z))
            while ("log" in block.id or "leaves" in block.id or "mushroom" in block.id) and start > 0:
                start = start - 1
                block = editor.getBlock((x, start - 1, z))
            if "dirt" in block.id:
                editor.placeBlock((x, start - 1, z), Block("air"))
            for y in range(start, end):
                editor.placeBlock((x, y, z), Block("air"))
    print("Done!")