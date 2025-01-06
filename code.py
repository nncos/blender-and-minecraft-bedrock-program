import bpy
from math import sqrt, floor, ceil
from numpy import arange

#====================================================
#constants
block_data = [    #colour, id, name
    ((205, 212, 212), 0, "concrete"),            #white
    ((213, 91, 16), 1, "concrete"),             #orange
    ((152, 40, 141), 2, "concrete"),           #magenta
    ((34, 121, 185), 3, "concrete"),        #light_blue
    ((237, 172, 27), 4, "concrete"),            #yellow
    ((82, 158, 25), 5, "concrete"),               #lime
    ((203, 91, 131), 6, "concrete"),              #pink
    ((42, 46, 49), 7, "concrete"),                #gray
    ((113, 113, 102), 8, "concrete"),       #light_gray
    ((22, 103, 124), 9, "concrete"),              #cyan
    ((86, 24, 139), 10, "concrete"),            #purple
    ((36, 35, 126), 11, "concrete"),              #blue
    ((82, 47, 24), 12, "concrete"),              #brown
    ((59, 76, 27), 13, "concrete"),              #green
    ((123, 28, 26), 14, "concrete"),               #red
    ((6, 5, 8), 15, "concrete"),                 #black

    ((37, 22 ,16), "", "black_terracotta"),
    ((77, 51 ,35), "", "brown_terracotta"),
    ((143, 61 ,46), "", "red_terracotta"),
    ((209, 178 ,161), "", "white_terracotta"),
    ((57, 42 ,35), "", "gray_terrracotta"),
    ((74, 59 ,91), "", "blue_terracotta"),
    ((86, 91 ,91), "", "cyan_terracotta"),
    ((76, 83 ,42), "", "green_terracotta"),
    ((113, 108 ,137), "", "light_blue_terracotta"),
    ((135, 106 ,97), "", "light_gray_terracotta"),
    ((103, 117 ,52), "", "lime_terracotta"),   
    ((186, 133 ,35), "", "yellow_terracotta"),
    ((161, 78 ,78), "", "pink_terracotta"),
    ((118, 70 ,86), "", "purple_terracotta"),
    ((161, 83 ,37), "", "orange_terracotta"),
    ((149, 88 ,108), "", "magenta_terracotta"),
    ((152, 94 ,67), "", "hardened_clay"),

    ((116, 167 ,253), "", "blue_ice"),
    ((141, 180 ,250), "", "packed_ice"),
    ((160, 166 ,179), "", "clay"),
    ((30, 67 ,140), "", "lapis_block"),
    ((149, 111 ,81), "", "brown_mushroom_block"),
    ((203, 196 ,185), "", "mushroom_stem"),
    ((125, 125 ,125), "", "stone")
]
world = "28rC7MeTQy4="
file_path_add = rf"C:\Users\c\AppData\Local\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\minecraftWorlds\{world}\behavior_packs\Functionsf\functions\add"     #use your own world file       
file_path_rmv = rf"C:\Users\c\AppData\Local\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\minecraftWorlds\{world}\behavior_packs\Functionsf\functions\remove"  #use your own world file
resolution = 0.4   #the smaller it is, the higher the quality, but requires more intense calculations (for larger builds, use a lower quality). doesnt change the number of setblock commands
speed = 0.2        #the smaller it is, the faster it updates the function   

#cache variables
object_data_sets = [set(), set()]        #new, old
obj_old = [None]
color_layer = [None]
warned = [False]

#====================================================
#functions
def convert_colors(poly, idx):
    """Match a vertex color to the nearest predefined concrete color."""
    r, g, b = color_layer[0].data[poly.loop_indices[idx]].color[:3]
    rgb = (r * 256, g * 256, b * 256)
    # Match to nearest color
    closest_index = min(
        range(len(block_data)),
        key=lambda i: sum(abs(c - sc) for c, sc in zip(rgb, block_data[i][0]))
    )
    return block_data[closest_index][1], block_data[closest_index][2]
    
def magnitude_and_direction(a,b):
    x1, y1, z1 = a
    x2, y2, z2 = b
    dx, dy, dz = (x2 - x1, y2 - y1, z2 - z1)
    magnitude = sqrt(dx**2 + dy**2 + dz**2)
    if magnitude == 0:
        return 0, (0, 0, 0)
    direction = (dx/magnitude, dy/magnitude, dz/magnitude)
    return magnitude, direction

#Fill in triangle
def fill_triangle(triangle, id, block):
    triangle_coords = set()
    magnitude1, direction1 = magnitude_and_direction(triangle[0],triangle[1])
    for t in arange(0, magnitude1, resolution):
        p = (
            triangle[0][0] + t * direction1[0],
            triangle[0][1] + t * direction1[1],
            triangle[0][2] + t * direction1[2],
        )
        magnitude2, direction2 = magnitude_and_direction(p, triangle[2])
        triangle_coords.update((
            floor(p[0] + t2 * direction2[0]),
            floor(p[1] + t2 * direction2[1]), 
            floor(p[2] + t2 * direction2[2]))
            for t2 in arange(0, magnitude2, resolution))
    object_data_sets[0].add((id, block, frozenset(triangle_coords)))
    
def tessellate_polygon(coords):
    """Tessellate a polygon with more than 3 vertices into triangles."""
    triangles = []
    for i in range(1, len(coords) - 1):
        triangles.append([coords[0], coords[i], coords[i + 1], i])
    return triangles

def process_mesh(mesh):
    """Process the mesh and convert polygons to blocks."""
    object_data_sets[0].clear()
    for poly in mesh.polygons:
        coords = [mesh.vertices[v_idx].co[:] for v_idx in poly.vertices]
        if len(coords) < 3:
            print(f"Skipped invalid polygon with {len(coords)} vertices.")
            continue
        if len(coords) == 3:  # Triangle
            color_id, block = convert_colors(poly, 1)
            fill_triangle(coords, color_id, block)
        else:  # Tessellate n-sided polygon into triangles
            triangles= tessellate_polygon(coords)
            for triangle in triangles:
                color_id, block = convert_colors(poly, triangle[3])
                fill_triangle(triangle, color_id, block)

def write_commands(set, file_path, command):
    length = sum(len(poly[2]) for poly in set)
    if length == 0:
        for i in range(5):
            open(f"{file_path}{i}.mcfunction", "w").close()
    elif 0 < length <= 10000:
        file = open(f"{file_path}0.mcfunction", "w")
        file.writelines(command.format(y, z, x, block, id) for id, block, coords in set for x, y, z in coords)
        file.close()
    elif 10000 < length <= 50000:
        idx = 0
        count = 0
        file = open(f"{file_path}0.mcfunction", "a")
        for id, block, coords in set:
            for x, y, z in coords:
                if count == 10000:  # Check if the count has reached 10,000
                    file.close()  # Close the current file
                    idx += 1  # Increment the file index
                    file = open(f"{file_path}{idx}.mcfunction", "a")  # Open a new file
                    count = 0
                file.write(command.format(y, z, x, block, id))
                count += 1
        file.close()
    else:
        print("The model is too big")

#====================================================
def loop():
    """Main loop for processing and updating commands."""
    obj = bpy.context.active_object
    add = set()
    remove = set()
    
    if obj != None and obj.mode != 'EDIT':
        
        if warned: 
            warned[0] = False
        
        #allows multiple objects
        mesh = obj.data
        if obj != obj_old[0]:
            obj_old[0] = obj
            object_data_sets[1].clear()
            try:
                if not mesh.vertex_colors:
                    mesh.vertex_colors.new()
                color_layer[0] = mesh.vertex_colors.active
            except AttributeError:
                print("Select another object")
                return speed
            
        try:
            process_mesh(mesh)
        except:
            return speed

        if object_data_sets[0] != object_data_sets[1]:
            remove = object_data_sets[1] - object_data_sets[0]
            add = object_data_sets[0] - object_data_sets[1]
            #print(len(object_data_sets[0]), len(object_data_sets[1]), len(add), len(remove))
            object_data_sets[1] = object_data_sets[0].copy()

    else:
        if warned[0] == False:
            print('Use object mode or select an object')
            if obj == None:
                remove = object_data_sets[0].copy()
            warned[0] = True

    write_commands(add, file_path_add, "setblock {0} {1} {2} {3} {4}\n")
    write_commands(remove, file_path_rmv, "setblock {0} {1} {2} air\n")

    return speed

#====================================================

bpy.app.timers.register(loop)

print('end')
