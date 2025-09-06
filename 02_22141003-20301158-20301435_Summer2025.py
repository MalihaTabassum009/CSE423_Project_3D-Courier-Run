from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

WINDOW_WIDTH = 1203
WINDOW_HEIGHT = 803
ARENA_SIZE = 402  
TILE_SIZE = 51    
PLAYER_SPEED_NORMAL = 156.0  
PLAYER_SPEED_SPRINT = 250.0  
PLAYER_ROTATION_SPEED = 135.0 
PLAYER_RADIUS = 15           
STAMINA_MAX = 100.0
STAMINA_DRAIN_RATE = 20.0    
STAMINA_REGEN_RATE = 10.0    


game_state = 'playing'  
time_left = 155.0       
total_score = 0
completed_deliveries = 0
difficulty_level = 1    # Feature 18: Difficulty Scaling

player_pos = [-300.0, 15.0, -300.0] 
player_angle = 0.0            
player_speed = PLAYER_SPEED_NORMAL
stamina = STAMINA_MAX
PLAYER_BOUND_MARGIN_X = 14.0   
PLAYER_BOUND_MARGIN_Z = 16.0   

key_states = {} 

camera_mode_is_follow = False 
camera_pos_fixed = [0, 500, 600] 

cam_orbit_radius = math.hypot(camera_pos_fixed[0], camera_pos_fixed[2])       
cam_orbit_angle_deg = math.degrees(math.atan2(camera_pos_fixed[0],            
                                              camera_pos_fixed[2]))

follow_back  = 66.0     
follow_up    = 30.0     
follow_side  = 9.0      
look_ahead   = 42.0     

follow_eye = [0.0, 0.0, 0.0]
follow_ctr = [0.0, 0.0, 0.0]
follow_smooth = 0.20    

packages = []
route_beacons = []
current_beacon_index = 0
route_color = (0,0,0) 
is_carrying_package = False
carried_package_info = None

special_tiles = []
spikes = []
gates = []
bonus_rings = []
game_time = 0.0 

# Feature 9: Conveyor Tiles
conveyor_tiles = []

# Feature 11: Pop-Up Spikes  
spike_cycle_time = 3.0  

# Feature 12: Dynamic Route Gates
gate_cycle_time = 4.0   

# Feature 14: Bonus Rings
bonus_ring_spawn_timer = 0.0
bonus_ring_spawn_interval = 15.0  

# Feature 16: Clean-Turn Combo
clean_turn_combo = 0
last_turn_time = 0.0
combo_threshold_frames = 30  
current_turn_frames = 0
last_player_speed = 0.0

# Feature 13: HUD Arrow
arrow_size = 20

last_frame_time = 0.0

COLOR_RED = (1, 0, 0)
COLOR_GREEN = (0, 1, 0)
COLOR_BLUE = (0, 0, 1)
COLOR_YELLOW = (1, 1, 0)
COLOR_MAGENTA = (1, 0, 1)
COLOR_CYAN = (0, 1, 1)
COLOR_WHITE = (1, 1, 1)
COLOR_GRAY = (0.5, 0.5, 0.5)
COLOR_BLACK = (0, 0, 0)
COLOR_ORANGE = (1, 0.5, 0)
COLOR_DARK_GRAY = (0.3, 0.3, 0.3)
ROUTE_COLORS = [COLOR_BLUE, COLOR_YELLOW, COLOR_MAGENTA, COLOR_CYAN]



def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=COLOR_WHITE):
    """
    This function draws 2D text on the screen. It's used for the HUD.
    It works by temporarily switching to a 2D orthographic view.
    """
    glColor3f(*color) 
    glMatrixMode(GL_PROJECTION)
    glPushMatrix() 
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT) 

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix() 
    glLoadIdentity()

    glRasterPos2f(x, y) 
    for char in text:
        glutBitmapCharacter(font, ord(char)) 

    glPopMatrix() 
    glMatrixMode(GL_PROJECTION)
    glPopMatrix() 
    glMatrixMode(GL_MODELVIEW)

def draw_cylinder(pos, radius, height, color):
    """A helper function to draw a simple cylinder."""
    glPushMatrix()
    glColor3f(*color)
    glTranslatef(pos[0], pos[1], pos[2])
    glRotatef(-90, 1, 0, 0) 
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, 20, 20)
    glTranslatef(0,0,height)
    gluDisk(quad, 0, radius, 20, 1)
    glPopMatrix()


def draw_arena():
    """Draws the checkerboard floor and the four colored boundary walls."""
    # Feature 1: 3D Arena & Floor
    glPushMatrix()
    num_tiles = ARENA_SIZE // TILE_SIZE
    for i in range(-num_tiles, num_tiles):
        for j in range(-num_tiles, num_tiles):
            if (i + j) % 2 == 0:
                glColor3f(0.8, 0.8, 0.8)
            else:
                glColor3f(0.6, 0.6, 0.6)

            glBegin(GL_QUADS)
            glVertex3f(i * TILE_SIZE, 0, j * TILE_SIZE)
            glVertex3f((i + 1) * TILE_SIZE, 0, j * TILE_SIZE)
            glVertex3f((i + 1) * TILE_SIZE, 0, (j + 1) * TILE_SIZE)
            glVertex3f(i * TILE_SIZE, 0, (j + 1) * TILE_SIZE)
            glEnd()
    glPopMatrix()

    wall_height = 100
    glPushMatrix()
    glColor3f(*COLOR_RED)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, ARENA_SIZE); glEnd()
    glColor3f(*COLOR_GREEN)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, -ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    glColor3f(*COLOR_BLUE)
    glBegin(GL_QUADS); glVertex3f(ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    glColor3f(*COLOR_YELLOW)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(-ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    glPopMatrix()

    # Feature 10: Low Sticky Tiles - Draw Special Tiles
    for tile in special_tiles:
        x, z, tile_type = tile['pos'][0], tile['pos'][2], tile['type']
        if tile_type == 'sticky':
            color = COLOR_DARK_GRAY
            glColor4f(color[0], color[1], color[2], 0.8) 
            glPushMatrix()
            glTranslatef(0, 1, 0) 
            glBegin(GL_QUADS)
            glVertex3f(x, 0, z); glVertex3f(x+TILE_SIZE, 0, z); glVertex3f(x+TILE_SIZE, 0, z+TILE_SIZE); glVertex3f(x, 0, z+TILE_SIZE);
            glEnd()
            glPopMatrix()

    # Feature 9: Conveyor Tiles (Directional Push)
    for conveyor in conveyor_tiles:
        x, z = conveyor['pos'][0], conveyor['pos'][2]
        direction = conveyor['direction']
        
        glColor3f(*COLOR_ORANGE)
        glPushMatrix()
        glTranslatef(0, 2, 0) 
        glBegin(GL_QUADS)
        glVertex3f(x, 0, z); glVertex3f(x+TILE_SIZE, 0, z); glVertex3f(x+TILE_SIZE, 0, z+TILE_SIZE); glVertex3f(x, 0, z+TILE_SIZE);
        glEnd()
        glPopMatrix()
        
        glColor3f(*COLOR_YELLOW)
        arrow_x = x + TILE_SIZE/2
        arrow_z = z + TILE_SIZE/2
        glPushMatrix()
        glTranslatef(arrow_x, 3, arrow_z)
        
        glBegin(GL_TRIANGLES)
        arrow_size = 10
        if direction == 'north':
            glVertex3f(0, 0, -arrow_size)
            glVertex3f(-arrow_size/2, 0, arrow_size/2)
            glVertex3f(arrow_size/2, 0, arrow_size/2)
        elif direction == 'south':
            glVertex3f(0, 0, arrow_size)
            glVertex3f(-arrow_size/2, 0, -arrow_size/2)
            glVertex3f(arrow_size/2, 0, -arrow_size/2)
        elif direction == 'east':
            glVertex3f(arrow_size, 0, 0)
            glVertex3f(-arrow_size/2, 0, -arrow_size/2)
            glVertex3f(-arrow_size/2, 0, arrow_size/2)
        elif direction == 'west':
            glVertex3f(-arrow_size, 0, 0)
            glVertex3f(arrow_size/2, 0, -arrow_size/2)
            glVertex3f(arrow_size/2, 0, arrow_size/2)
        glEnd()
        glPopMatrix()


def draw_player():
    """Feature 3: Player Avatar & Movement - Draws the player character as a composite object."""
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0, 1, 0)

    glColor3f(0.2, 0.4, 0.8)
    glPushMatrix(); glScalef(1, 1.5, 0.8); glutSolidCube(20); glPopMatrix()

    glColor3f(0.8, 0.6, 0.4)
    glPushMatrix(); glTranslatef(0, 25, 0); glutSolidSphere(10, 20, 20); glPopMatrix()

    glColor3f(1, 1, 1)
    glPushMatrix(); glTranslatef(0, 15, -10); glutSolidCube(5); glPopMatrix()

    # Feature 15: Package Interaction - If carrying a package, draw it
    if is_carrying_package:
        glColor3f(*carried_package_info['color'])
        glPushMatrix(); glTranslatef(20, 10, 0); glutSolidCube(10); glPopMatrix()

    glPopMatrix()

def clamp_player_inside_arena(old_x, old_z):
    """
    Keep player within an inner rectangle:
      x ∈ [-(ARENA_SIZE - margin_x), +(ARENA_SIZE - margin_x)]
      z ∈ [-(ARENA_SIZE - margin_z), +(ARENA_SIZE - margin_z)]
    If only one axis violates, we revert just that axis (nice wall sliding).
    """
    inner_x = ARENA_SIZE - PLAYER_BOUND_MARGIN_X
    inner_z = ARENA_SIZE - PLAYER_BOUND_MARGIN_Z

    if player_pos[0] >  inner_x: player_pos[0] = inner_x
    if player_pos[0] < -inner_x: player_pos[0] = -inner_x

    if player_pos[2] >  inner_z: player_pos[2] = inner_z
    if player_pos[2] < -inner_z: player_pos[2] = -inner_z

def draw_packages():
    """Feature 5: Package System - Draws all packages at the package station."""
    for pkg in packages:
        if not pkg['is_carried']:
            glPushMatrix()
            glTranslatef(pkg['pos'][0], pkg['pos'][1], pkg['pos'][2])
            glColor3f(*pkg['color'])
            glutSolidCube(15)
            glColor3f(1,1,1); glTranslatef(0,8,0); glutSolidCube(5)
            glPopMatrix()

def draw_beacons():
    """Feature 6: Ordered Checkpoints & Drop Zone - Draws the route beacons, highlighting the current one."""
    for i, beacon in enumerate(route_beacons):
        is_current = (i == current_beacon_index)
        base_color = beacon['color']

        if i == len(route_beacons) - 1: 
            color = COLOR_WHITE
        elif is_current:
            brightness = 0.6 + 0.4 * (math.sin(game_time * 5) + 1) / 2
            color = (base_color[0]*brightness, base_color[1]*brightness, base_color[2]*brightness)
        else: 
             color = (base_color[0]*0.2, base_color[1]*0.2, base_color[2]*0.2)

        draw_cylinder(beacon['pos'], 10, 100, color)


def draw_hazards():
    """Feature 11: Pop-Up Spikes & Feature 12: Dynamic Route Gates - Draws dynamic hazards like spikes and gates."""
    # Feature 11: Draw Spikes
    for spike in spikes:
        # Color changes based on danger state
        if spike.get('is_dangerous', False) and spike['current_height'] > 40:
            # Dangerous spike - bright red
            color = (1.0, 0.1, 0.1)
        elif spike['current_height'] > 5:
            # Rising/falling spike - orange warning
            color = (1.0, 0.5, 0.0)
        else:
            # Safe spike - dark gray
            color = (0.3, 0.3, 0.3)
        
        draw_cylinder(spike['pos'], 12, spike['current_height'], color)

    # Feature 12: Draw Gates
    for gate in gates:
        glPushMatrix()
        glTranslatef(gate['pos'][0], gate['current_height']/2, gate['pos'][2])
        
        if gate['is_open']:
            glColor3f(*COLOR_GREEN)
        else:
            glColor3f(*COLOR_RED)
            
        if gate['orientation'] == 'vertical':
            glScalef(5, gate['current_height'], 50)
        else:
            glScalef(50, gate['current_height'], 5)
            
        glutSolidCube(1)
        glPopMatrix()

def draw_bonus_rings():
    """Feature 14: Bonus Rings - Draws floating bonus rings."""
    for ring in bonus_rings:
        if ring['active']:
            glPushMatrix()
            glTranslatef(ring['pos'][0], ring['pos'][1], ring['pos'][2])
            glColor3f(*COLOR_YELLOW)
            for i in range(20):
                angle = math.radians(i * 18)
                x = ring['radius'] * math.cos(angle)
                z = ring['radius'] * math.sin(angle)
                glPushMatrix()
                glTranslatef(x, 0, z)
                glutSolidSphere(3, 10, 10)
                glPopMatrix()
            glPopMatrix()


def draw_hud_arrow():
    """Feature 13: HUD Arrow to Next Beacon - Draws arrow pointing to next beacon"""
    if len(route_beacons) > 0 and current_beacon_index < len(route_beacons):
        target_pos = route_beacons[current_beacon_index]['pos']
        dx = target_pos[0] - player_pos[0]
        dz = target_pos[2] - player_pos[2]
        target_angle_world = math.degrees(math.atan2(dx, dz))
        arrow_angle = target_angle_world - player_angle

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glTranslatef(WINDOW_WIDTH / 2, WINDOW_HEIGHT - 100, 0)
        glRotatef(-arrow_angle, 0, 0, 1) 
        glColor3f(*COLOR_YELLOW)
        
        glBegin(GL_TRIANGLES)
        glVertex2f(0, arrow_size)
        glVertex2f(-arrow_size/2, -arrow_size/2)
        glVertex2f(arrow_size/2, -arrow_size/2)
        glEnd()
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def draw_hud():
    """Feature 8: Global Timer + Medals - Draws the Heads-Up Display with all game information."""
    # Feature 8: Time and Medal Status
    minutes = int(time_left // 60)
    seconds = int(time_left % 60)
    draw_text(10, WINDOW_HEIGHT - 30, f"Time Left: {minutes:02d}:{seconds:02d}")
    
    medal_type = "NO MEDAL"
    if time_left >= 120:
        medal_type = "GOLD"
    elif time_left >= 60:
        medal_type = "SILVER"
    elif time_left >= 1:
        medal_type = "BRONZE"
    draw_text(10, WINDOW_HEIGHT - 60, f"Medal Status: {medal_type}")

    draw_text(10, WINDOW_HEIGHT - 90, f"Score: {total_score}")

    # Feature 15: Package Status
    status = "Empty"
    color = COLOR_WHITE
    if is_carrying_package:
        if carried_package_info['is_correct']:
            status = "Correct Package"
            color = COLOR_GREEN
        else:
            status = "WRONG PACKAGE!"
            color = COLOR_RED
    draw_text(200, WINDOW_HEIGHT - 30, f"Package: {status}", color=color)

    # Feature 6: Checkpoint
    draw_text(200, WINDOW_HEIGHT - 60, f"Next Beacon: {current_beacon_index + 1} / {len(route_beacons)}")

    # Feature 4: Stamina Bar
    draw_text(10, 80, "Stamina")
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(10, 50)
    glVertex2f(210, 50)
    glVertex2f(210, 70)
    glVertex2f(10, 70)
    glEnd()
    
    stamina_width = 200 * (stamina / STAMINA_MAX)
    glColor3f(0, 0.8, 0)
    glBegin(GL_QUADS)
    glVertex2f(10, 50)
    glVertex2f(10 + stamina_width, 50)
    glVertex2f(10 + stamina_width, 70)
    glVertex2f(10, 70)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Feature 16: Clean-Turn Combo
    if clean_turn_combo > 0:
        draw_text(WINDOW_WIDTH - 150, 80, f"Combo: {clean_turn_combo}x", color=COLOR_YELLOW)

    # Feature 18: Difficulty Level
    draw_text(WINDOW_WIDTH - 150, 50, f"Difficulty: {difficulty_level}")

    # Feature 17: Pause message
    if game_state == 'paused':
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glColor4f(0, 0, 0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(WINDOW_WIDTH, 0)
        glVertex2f(WINDOW_WIDTH, WINDOW_HEIGHT)
        glVertex2f(0, WINDOW_HEIGHT)
        glEnd()
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        draw_text(WINDOW_WIDTH/2 - 50, WINDOW_HEIGHT/2, "PAUSED", font=GLUT_BITMAP_TIMES_ROMAN_24)

    # Feature 13: Draw HUD arrow
    draw_hud_arrow()


def get_distance(p1, p2):
    """Calculates the 2D distance between two points [x, y, z]."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[2] - p2[2])**2)

def start_new_delivery():
    """Resets and randomizes the game for a new delivery run."""
    global route_color, current_beacon_index, packages, route_beacons, bonus_rings, special_tiles, conveyor_tiles
    
    current_beacon_index = 0
    route_beacons.clear()
    packages.clear()
    bonus_rings.clear()
    special_tiles.clear()
    conveyor_tiles.clear()

    old_color = route_color
    while route_color == old_color:
        route_color = random.choice(ROUTE_COLORS)

    for i in range(4): 
        pos = [random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50), 0, random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50)]
        route_beacons.append({'pos': pos, 'color': route_color})
    pos = [random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50), 0, random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50)]
    route_beacons.append({'pos': pos, 'color': COLOR_WHITE})

    correct_pkg_pos = [random.uniform(-350, -250), 7.5, random.uniform(-350, -250)]
    packages.append({'pos': correct_pkg_pos, 'color': route_color, 'is_correct': True, 'is_carried': False})
    decoy_colors = [c for c in ROUTE_COLORS if c != route_color]
    for i in range(random.randint(2,3)):
        pos = [random.uniform(-350, -250), 7.5, random.uniform(-350, -250)]
        packages.append({'pos': pos, 'color': random.choice(decoy_colors), 'is_correct': False, 'is_carried': False})
        
    # 5. Feature 14: Generate bonus rings
    ring_count = random.randint(3, 5) + difficulty_level  
    for i in range(ring_count):
        pos = [random.uniform(-ARENA_SIZE, ARENA_SIZE), 60, random.uniform(-ARENA_SIZE, ARENA_SIZE)]
        bonus_rings.append({'pos': pos, 'radius': 30, 'active': True, 'multiplier': 1})
        
    # 6. Feature 10: Generate sticky tiles
    for i in range(5):
        x = random.randint(-8, 7) * TILE_SIZE
        z = random.randint(-8, 7) * TILE_SIZE
        special_tiles.append({'pos': [x,0,z], 'type': 'sticky'})
        
    # 7. Feature 9: Generate conveyor tiles
    for i in range(8):
        x = random.randint(-8, 7) * TILE_SIZE
        z = random.randint(-8, 7) * TILE_SIZE
        direction = random.choice(['north', 'south', 'east', 'west'])
        conveyor_tiles.append({'pos': [x, 0, z], 'direction': direction, 'strength': 30.0})

def Update_fixed_cam_from_orbit():
    """Recompute camera_pos_fixed.x/z from (radius, angle)."""
    rad = math.radians(cam_orbit_angle_deg)
    camera_pos_fixed[0] = cam_orbit_radius * math.sin(rad)   
    camera_pos_fixed[2] = cam_orbit_radius * math.cos(rad)   

def Compute_follow_targets():
    """Return (eye_xyz, ctr_xyz) for the OTS follow camera based on player pose."""
    rad = math.radians(player_angle)
    fwdx, fwdz = math.sin(rad), math.cos(rad)         
    rtx, rtz   = fwdz, -fwdx                          

    eye_x = player_pos[0] - fwdx*follow_back + rtx*follow_side
    eye_y = player_pos[1] + follow_up
    eye_z = player_pos[2] - fwdz*follow_back + rtz*follow_side

    ctr_x = player_pos[0] + fwdx*look_ahead
    ctr_y = player_pos[1] + follow_up*0.3
    ctr_z = player_pos[2] + fwdz*look_ahead
    return (eye_x, eye_y, eye_z), (ctr_x, ctr_y, ctr_z)

def init_game():
    """Initializes or resets the entire game to its starting state."""
    global game_state, time_left, total_score, player_pos, player_angle, stamina
    global last_frame_time, game_time, completed_deliveries, is_carrying_package, carried_package_info
    global difficulty_level, clean_turn_combo, bonus_ring_spawn_timer
    
    print("Initializing new game...")
    game_state = 'playing'
    time_left = 156.0
    total_score = 0
    completed_deliveries = 0
    difficulty_level = 1
    player_pos = [-300.0, 15.0, -300.0]
    player_angle = 0.0
    stamina = STAMINA_MAX
    is_carrying_package = False
    carried_package_info = None
    clean_turn_combo = 0
    bonus_ring_spawn_timer = 0.0
    
    # Feature 11 & 12: Initialize hazards (spikes and gates)
    spikes.clear()
    gates.clear()
    
    # Feature 11: Create spikes
    for i in range(5):
        pos = [random.uniform(-ARENA_SIZE, ARENA_SIZE), 0, random.uniform(-ARENA_SIZE, ARENA_SIZE)]
        spikes.append({
            'pos': pos, 
            'current_height': 0, 
            'max_height': 80,
            'cycle_offset': random.uniform(0, 2*math.pi)
        })
    
    # Feature 12: Create gates
    for i in range(3):
        gate_pos = [random.uniform(-ARENA_SIZE/2, ARENA_SIZE/2), 0, random.uniform(-ARENA_SIZE/2, ARENA_SIZE/2)]
        orientation = random.choice(['vertical', 'horizontal'])
        gates.append({
            'pos': gate_pos, 
            'current_height': 0, 
            'max_height': 100,
            'is_open': True,
            'orientation': orientation,
            'cycle_offset': random.uniform(0, 2*math.pi)
        })

    start_new_delivery() 
    last_frame_time = time.time()
    game_time = 0.0

def update_player(delta_time):
    """Updates player position, rotation, and stamina based on input."""
    global player_pos, player_angle, player_speed, stamina, clean_turn_combo, last_turn_time
    global current_turn_frames, last_player_speed

    # Feature 4: Sprinting and Stamina
    is_sprinting = key_states.get(b'shift', False) and stamina > 0
    if is_sprinting:
        player_speed = PLAYER_SPEED_SPRINT
        stamina -= STAMINA_DRAIN_RATE * delta_time
    else:
        player_speed = PLAYER_SPEED_NORMAL
        if stamina < STAMINA_MAX:
            stamina += STAMINA_REGEN_RATE * delta_time
    stamina = max(0, min(stamina, STAMINA_MAX)) 

    # Feature 3: Rotation
    is_turning = False
    if key_states.get(b'a', False):
        player_angle -= PLAYER_ROTATION_SPEED * delta_time
        is_turning = True
    if key_states.get(b'd', False):
        player_angle += PLAYER_ROTATION_SPEED * delta_time
        is_turning = True

    # Feature 3: Forward/Backward Movement
    move_dir = 0
    if key_states.get(b'w', False):
        move_dir = 1
    if key_states.get(b's', False):
        move_dir = -1

    old_x, old_z = player_pos[0], player_pos[2]
    
    current_speed = player_speed
    
    # Feature 10: Check for sticky tiles (reduce speed)
    on_sticky_tile = False
    for tile in special_tiles:
        if tile['type'] == 'sticky':
            x, z = tile['pos'][0], tile['pos'][2]
            if x <= player_pos[0] <= x + TILE_SIZE and z <= player_pos[2] <= z + TILE_SIZE:
                current_speed *= 0.2  
                on_sticky_tile = True
                break

    if move_dir != 0:
        angle_rad = math.radians(player_angle)
        dx = math.sin(angle_rad) * current_speed * delta_time
        dz = math.cos(angle_rad) * current_speed * delta_time
        player_pos[0] += dx * move_dir
        player_pos[2] += dz * move_dir

    # Feature 9: Apply conveyor tile effects
    for conveyor in conveyor_tiles:
        x, z = conveyor['pos'][0], conveyor['pos'][2]
        if x <= player_pos[0] <= x + TILE_SIZE and z <= player_pos[2] <= z + TILE_SIZE:
            push_strength = conveyor['strength'] * delta_time
            if conveyor['direction'] == 'north':
                player_pos[2] -= push_strength
            elif conveyor['direction'] == 'south':
                player_pos[2] += push_strength
            elif conveyor['direction'] == 'east':
                player_pos[0] += push_strength
            elif conveyor['direction'] == 'west':
                player_pos[0] -= push_strength

    # Feature 16: Clean-Turn Combo Logic
    speed_threshold = 50.0  
    if is_turning and move_dir == 1 and current_speed > speed_threshold:
        current_turn_frames += 1
        if current_turn_frames >= combo_threshold_frames:
            clean_turn_combo += 1
            current_turn_frames = 0
            global time_left
            time_left += 2.0
    elif not is_turning or move_dir != 1 or current_speed <= speed_threshold:
        if current_turn_frames > 0:
            current_turn_frames = 0
        if time.time() - last_turn_time > 2.0:
            clean_turn_combo = 0
    
    if is_turning:
        last_turn_time = time.time()
    
    last_player_speed = current_speed

    clamp_player_inside_arena(old_x, old_z)

def update_hazards(delta_time):
    """Feature 11 & 12: Animates spikes and gates with difficulty scaling."""
    global difficulty_level
    
    # Feature 18: Difficulty scaling - faster cycles at higher difficulty
    spike_speed_multiplier = 1.0 + (difficulty_level - 1) * 0.3
    gate_speed_multiplier = 1.0 + (difficulty_level - 1) * 0.2
    
    # Feature 11: Update spike heights using a sine wave for smooth animation
    for spike in spikes:
        cycle_time = spike_cycle_time / spike_speed_multiplier
        spike_phase = (game_time / cycle_time + spike['cycle_offset']) % (2 * math.pi)
        # Make spikes more obvious - fully up or fully down with quick transitions
        sin_value = math.sin(spike_phase)
        if sin_value > 0.3:
            # Spike is up (dangerous)
            spike['current_height'] = spike['max_height']
            spike['is_dangerous'] = True
        elif sin_value < -0.3:
            # Spike is down (safe)
            spike['current_height'] = 0
            spike['is_dangerous'] = False
        else:
            # Transition phase - linear interpolation for quick movement
            if sin_value > 0:
                # Rising
                transition_ratio = (sin_value - 0.3) / 0.7  # 0.3 to 1.0 -> 0 to 1
                spike['current_height'] = spike['max_height'] * max(0, transition_ratio)
                spike['is_dangerous'] = False
            else:
                # Falling
                transition_ratio = (sin_value + 0.3) / 0.7  # -1.0 to -0.3 -> 1 to 0
                spike['current_height'] = spike['max_height'] * max(0, transition_ratio)
                spike['is_dangerous'] = False

    # Feature 12: Update gate positions
    for gate in gates:
        cycle_time = gate_cycle_time / gate_speed_multiplier
        gate_phase = (game_time / cycle_time + gate['cycle_offset']) % (2 * math.pi)
        gate['is_open'] = math.sin(gate_phase) > 0
        gate['current_height'] = 0 if gate['is_open'] else gate['max_height']

def update_bonus_rings(delta_time):
    """Feature 14: Update bonus ring spawning and effects"""
    global bonus_ring_spawn_timer, difficulty_level
    
    bonus_ring_spawn_timer += delta_time
    
    # Feature 18: Spawn extra rings more frequently at higher difficulty
    spawn_interval = bonus_ring_spawn_interval / difficulty_level
    
    if bonus_ring_spawn_timer >= spawn_interval:
        bonus_ring_spawn_timer = 0.0
        angle_rad = math.radians(player_angle)
        ahead_distance = 150
        ring_x = player_pos[0] + math.sin(angle_rad) * ahead_distance
        ring_z = player_pos[2] + math.cos(angle_rad) * ahead_distance
        
        if abs(ring_x) < ARENA_SIZE and abs(ring_z) < ARENA_SIZE:
            bonus_rings.append({
                'pos': [ring_x, 60, ring_z], 
                'radius': 25, 
                'active': True,
                'multiplier': difficulty_level
            })

def handle_collisions_and_interactions(delta_time):
    """Manages all game interactions: pickups, beacon checks, hazard collisions."""
    global time_left, total_score, is_carrying_package, carried_package_info, current_beacon_index, completed_deliveries

    # Feature 15: Package Pickup/Drop Logic
    if key_states.get(b'u', False): 
        if not is_carrying_package:
            for pkg in packages:
                if not pkg['is_carried'] and get_distance(player_pos, pkg['pos']) < 30:
                    is_carrying_package = True
                    carried_package_info = pkg
                    pkg['is_carried'] = True
                    if not pkg['is_correct']:
                        time_left -= 5 
                    break 
        key_states[b'u'] = False 
    
    if key_states.get(b'f', False): 
        if is_carrying_package:
            carried_package_info['is_carried'] = False
            carried_package_info['pos'] = [player_pos[0], 7.5, player_pos[2]]
            is_carrying_package = False
            carried_package_info = None
        key_states[b'f'] = False

    # Feature 6: Beacon Check Logic
    if current_beacon_index < len(route_beacons):
        target_beacon = route_beacons[current_beacon_index]
        if get_distance(player_pos, target_beacon['pos']) < 30:
            if is_carrying_package and carried_package_info['is_correct']:
                if current_beacon_index == len(route_beacons) - 1:
                    total_score += 100
                    time_left += 10
                    completed_deliveries += 1
                    is_carrying_package = False 
                    if carried_package_info:
                        carried_package_info['is_carried'] = False
                    carried_package_info = None
                    
                    # Feature 18: Increase difficulty every few deliveries
                    global difficulty_level
                    if completed_deliveries % 3 == 0:
                        difficulty_level += 1
                    
                    start_new_delivery()
                else: 
                    total_score += 20
                    current_beacon_index += 1

    # Feature 11: Spike Collisions
    for spike in spikes:
        spike_distance = get_distance(player_pos, spike['pos'])
        spike_radius = 12  # Spike collision radius
        collision_distance = PLAYER_RADIUS + spike_radius
        
        if spike_distance < collision_distance:
            if spike.get('is_dangerous', False) and spike['current_height'] > 40:
                # Spike is up and dangerous - one-time penalty and knockback
                if not spike.get('hit_player', False):  # Only hit once per spike cycle
                    time_left -= 3.0  # One-time 3-second penalty
                    spike['hit_player'] = True
                    print(f"Spike hit! -3 seconds penalty. Time left: {time_left:.1f}")
                
                # Strong knockback every frame while touching dangerous spike
                angle_to_spike = math.atan2(spike['pos'][0] - player_pos[0], spike['pos'][2] - player_pos[2])
                knockback_distance = 80  # Strong immediate knockback
                player_pos[0] -= math.sin(angle_to_spike) * knockback_distance * delta_time
                player_pos[2] -= math.cos(angle_to_spike) * knockback_distance * delta_time
            else:
                # Spike is down or transitioning - solid collision (can't pass through)
                # Reset hit flag when spike is safe
                spike['hit_player'] = False
                
                # Calculate overlap and push player out
                overlap = collision_distance - spike_distance
                if overlap > 0:
                    angle_to_spike = math.atan2(spike['pos'][0] - player_pos[0], spike['pos'][2] - player_pos[2])
                    # Push player away from spike center
                    player_pos[0] -= math.sin(angle_to_spike) * (overlap + 2)
                    player_pos[2] -= math.cos(angle_to_spike) * (overlap + 2)
        else:
            # Player is far from spike - reset hit flag
            spike['hit_player'] = False

    # Feature 12: Gate Collisions
    for gate in gates:
        if not gate['is_open']:
            gate_distance = get_distance(player_pos, gate['pos'])
            gate_collision_radius = 30 if gate['orientation'] == 'vertical' else 40
            collision_distance = PLAYER_RADIUS + gate_collision_radius
            
            if gate_distance < collision_distance:
                # Calculate overlap and push player out completely
                overlap = collision_distance - gate_distance
                if overlap > 0:
                    angle_to_gate = math.atan2(gate['pos'][0] - player_pos[0], gate['pos'][2] - player_pos[2])
                    # Push player away from gate center
                    player_pos[0] -= math.sin(angle_to_gate) * (overlap + 5)  # Extra 5 units for solid feeling
                    player_pos[2] -= math.cos(angle_to_gate) * (overlap + 5)
                    time_left -= 0.5 * delta_time  # Small penalty for hitting closed gate 

    # Feature 14: Bonus Ring Collection
    for ring in bonus_rings[:]: 
        if ring['active'] and get_distance(player_pos, ring['pos']) < ring['radius']:
            time_bonus = 5 * ring['multiplier']
            score_bonus = 10 * ring['multiplier']
            time_left += time_bonus
            total_score += score_bonus
            ring['active'] = False
            bonus_rings.remove(ring)

def update_game(delta_time):
    """The main update function, called every frame from idle()."""
    global time_left, game_state, game_time
    
    game_time += delta_time 

    update_player(delta_time)
    update_hazards(delta_time)
    update_bonus_rings(delta_time)
    handle_collisions_and_interactions(delta_time)

    # Feature 8: Update main timer and check for failure
    time_left -= delta_time
    if time_left <= 0:
        time_left = 0
        game_state = 'fail'
        print("Game Over! You ran out of time.")


def keyboardListener(key, x, y):
    """Handles key down events."""
    global game_state
    key_states[key.lower()] = True 
    key_states[b'shift'] = glutGetModifiers() & GLUT_ACTIVE_SHIFT

    # Feature 17: Handle single-press actions like pause and reset
    if key == b'p' or key == b'P':
        game_state = 'paused' if game_state == 'playing' else 'playing'
    if key == b'r' or key == b'R':
        init_game() 

def keyboardUpListener(key, x, y):
    """Handles key up events."""
    key_states[key.lower()] = False 
    key_states[b'shift'] = glutGetModifiers() & GLUT_ACTIVE_SHIFT

def specialKeyListener(key, x, y):
    """
    Feature 2: Arrow keys:
      FIXED camera  : UP/DOWN = height, LEFT/RIGHT = orbit around arena center
      FOLLOW (OTS)  : UP/DOWN = nudge camera up/down, LEFT/RIGHT = shoulder peek
    """
    global camera_pos_fixed, cam_orbit_angle_deg, cam_orbit_radius
    global follow_up, follow_side

    if camera_mode_is_follow:
        STEP_UP   = 2.5     
        STEP_SIDE = 2.5     
        if key == GLUT_KEY_UP:    follow_up  += STEP_UP
        if key == GLUT_KEY_DOWN:  follow_up  -= STEP_UP
        if key == GLUT_KEY_LEFT:  follow_side -= STEP_SIDE
        if key == GLUT_KEY_RIGHT: follow_side += STEP_SIDE
        follow_up  = max(10.0, min(120.0, follow_up))
        follow_side = max(-50.0, min(50.0, follow_side))
    else:
        STEP_Y   = 30.0     
        STEP_ANG = 3.0      
        if key == GLUT_KEY_UP:    camera_pos_fixed[1] += STEP_Y
        if key == GLUT_KEY_DOWN:  camera_pos_fixed[1] -= STEP_Y
        camera_pos_fixed[1] = max(60.0, min(1500.0, camera_pos_fixed[1]))
        if key == GLUT_KEY_LEFT:  cam_orbit_angle_deg += STEP_ANG
        if key == GLUT_KEY_RIGHT: cam_orbit_angle_deg -= STEP_ANG
        Update_fixed_cam_from_orbit()

    glutPostRedisplay()

def mouseListener(button, state, x, y):
    """Feature 2: Handles mouse clicks."""
    global camera_mode_is_follow, follow_eye, follow_ctr
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode_is_follow = not camera_mode_is_follow       
        if camera_mode_is_follow:
            tgt_eye, tgt_ctr = Compute_follow_targets()
            follow_eye[:] = list(tgt_eye)
            follow_ctr[:] = list(tgt_ctr)
        glutPostRedisplay()

def setupCamera():
    """Feature 2: Configures the camera's projection and view settings."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, (WINDOW_WIDTH / WINDOW_HEIGHT), 0.1, 2000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode_is_follow:
        tgt_eye, tgt_ctr = Compute_follow_targets()
        s = follow_smooth
        for i in range(3):
            follow_eye[i] = follow_eye[i]*(1.0 - s) + tgt_eye[i]*s
            follow_ctr[i] = follow_ctr[i]*(1.0 - s) + tgt_ctr[i]*s

        gluLookAt(follow_eye[0], follow_eye[1], follow_eye[2],
                  follow_ctr[0], follow_ctr[1], follow_ctr[2],
                  0, 1, 0)
    else:
        gluLookAt(camera_pos_fixed[0], camera_pos_fixed[1], camera_pos_fixed[2],
                  0, 0, 0,
                  0, 1, 0)

def idle():
    """
    The main game loop, called continuously by GLUT.
    It calculates delta_time for frame-rate independent physics and logic.
    """
    global last_frame_time
    
    current_time = time.time()
    delta_time = current_time - last_frame_time
    last_frame_time = current_time

    if game_state == 'playing':
        update_game(delta_time)

    glutPostRedisplay()

def showScreen():
    """The main display function, responsible for all rendering."""
    # Feature 7: Clear the screen and enable depth testing
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST) # Feature 7: Depth Test On - Ensure 3D objects occlude each other correctly
    glEnable(GL_BLEND) 
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Feature 2: Set up the camera
    setupCamera()

    draw_arena()        # Feature 1: 3D Arena & Floor
    draw_player()       # Feature 3: Player Avatar & Movement  
    draw_packages()     # Feature 5: Package System
    draw_beacons()      # Feature 6: Ordered Checkpoints & Drop Zone
    draw_hazards()      # Feature 11: Pop-Up Spikes & Feature 12: Dynamic Route Gates
    draw_bonus_rings()  # Feature 14: Bonus Rings

    glDisable(GL_DEPTH_TEST)
    draw_hud()          # Feature 8: Global Timer + Medals, Feature 4: Sprint + Stamina Bar, etc.
    glEnable(GL_DEPTH_TEST)

    glutSwapBuffers()

def main():
    """Initializes GLUT and starts the main application loop."""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Courier Run 3D - Complete Features 1-18")

    # Feature 7: Enable depth testing
    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener) 
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    init_game() 

    print("--- Courier Run 3D - Features 1-18 ---")
    print("Controls:")
    print("W/S: Move Forward/Backward")
    print("A/D: Rotate Left/Right") 
    print("Shift: Sprint")
    print("U: Pick Up Package")
    print("F: Drop Package")
    print("Right Mouse Click: Toggle Camera Mode")
    print("Arrow Keys: Adjust Camera")
    print("P: Pause Game")
    print("R: Reset Game")
    print("")
    print("Features Implemented:")
    print("1-6: Arena, Camera, Player, Sprint, Packages, Beacons")
    print("7: Depth Test, 8: Timer/Medals, 9: Conveyors")
    print("10: Sticky Tiles, 11: Spikes, 12: Gates")
    print("13: HUD Arrow, 14: Bonus Rings, 15: Package Interaction")
    print("16: Clean-Turn Combo, 17: Pause/Reset, 18: Difficulty Scaling")
    
    glutMainLoop()

if __name__ == "__main__":
    main()
