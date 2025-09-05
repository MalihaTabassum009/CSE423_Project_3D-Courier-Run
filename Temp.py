# Import necessary libraries from PyOpenGL and standard Python modules
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

# --- A. GAME CONFIGURATION AND CONSTANTS ---
# These constants control the basic properties of the game world and player.
WINDOW_WIDTH = 1203
WINDOW_HEIGHT = 803
ARENA_SIZE = 402  # The half-length of the arena floor (e.g., from -400 to 400)
TILE_SIZE = 51    # The size of each checkerboard tile
PLAYER_SPEED_NORMAL = 156.0  # Player speed in units per second
PLAYER_SPEED_SPRINT = 250.0  # Player sprint speed
PLAYER_ROTATION_SPEED = 135.0 # Player rotation speed in degrees per second
PLAYER_RADIUS = 15           # Collision radius for the player
STAMINA_MAX = 100.0
STAMINA_DRAIN_RATE = 20.0    # Stamina drained per second of sprinting
STAMINA_REGEN_RATE = 10.0    # Stamina regenerated per second when not sprinting

# --- B. GAME STATE VARIABLES ---
# These variables store all the information about the current state of the game.
# They are initialized in the init_game() function.

# Core Game State
game_state = 'playing'  # Can be 'playing', 'paused', 'win', 'fail'
time_left = 155.0       # The main countdown timer
total_score = 0
completed_deliveries = 0

# Player State
player_pos = [0.0, 15.0, 0.0] # Player's [x, y, z] position. Y is height.
player_angle = 0.0            # Player's rotation angle around the Y-axis
player_speed = PLAYER_SPEED_NORMAL
stamina = STAMINA_MAX
# Keep the player's mesh inside the walls by this margin (in world units).
# Z margin is a bit bigger to account for the "nose" protruding forward.
PLAYER_BOUND_MARGIN_X = 14.0   # half-body width (~10) + safety
PLAYER_BOUND_MARGIN_Z = 16.0   # body (~8) + nose (10) ≈ 16


# Input State
key_states = {} # A dictionary to track which keys are currently held down

# Camera State
camera_mode_is_follow = False # Toggles between fixed and follow camera
camera_pos_fixed = [0, 500, 600] # Position for the fixed overview camera

# NEW ➜ fixed-camera orbit parameters (computed from the initial position)
cam_orbit_radius = math.hypot(camera_pos_fixed[0], camera_pos_fixed[2])       # distance from arena center
cam_orbit_angle_deg = math.degrees(math.atan2(camera_pos_fixed[0],            # angle around center (deg)
                                              camera_pos_fixed[2]))


# NEW — over-the-shoulder follow camera tuning
follow_back  = 66.0     # how far behind the head the camera sits
follow_up    = 30.0     # how high above the floor (rough head height)
follow_side  = 9.0      # shoulder peek ( + = over right shoulder, − = left )
look_ahead   = 42.0     # look a bit forward along facing

# follow_back = 2.0   # almost zero
# follow_up   = 28.0  # head height
# look_ahead  = 120.0 # longer look-ahead to reduce motion sickness


# NEW — soft-follow state (smoothed eye/center)
follow_eye = [0.0, 0.0, 0.0]
follow_ctr = [0.0, 0.0, 0.0]
follow_smooth = 0.20    # 0..1: higher = snappier movement
#-----------------------------------------------------------------------------------------


# Package & Route State
packages = []
route_beacons = []
current_beacon_index = 0
route_color = (0,0,0) # The correct color for the current delivery
is_carrying_package = False
carried_package_info = None

# Hazard & Environment State
special_tiles = []
spikes = []
gates = []
bonus_rings = []
game_time = 0.0 # A global timer that always increases, used for animations

# Combo State
clean_turn_combo = 0
last_turn_time = 0.0

# Time tracking for frame-rate independent movement
last_frame_time = 0.0

# --- C. COLOR DEFINITIONS ---
# Pre-defined colors to be used throughout the game for consistency.
COLOR_RED = (1, 0, 0)
COLOR_GREEN = (0, 1, 0)
COLOR_BLUE = (0, 0, 1)
COLOR_YELLOW = (1, 1, 0)
COLOR_MAGENTA = (1, 0, 1)
COLOR_CYAN = (0, 1, 1)
COLOR_WHITE = (1, 1, 1)
COLOR_GRAY = (0.5, 0.5, 0.5)
COLOR_BLACK = (0, 0, 0)
ROUTE_COLORS = [COLOR_BLUE, COLOR_YELLOW, COLOR_MAGENTA, COLOR_CYAN]


# --- D. HELPER AND DRAWING FUNCTIONS ---

### D1. Basic Drawing Helpers ###

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=COLOR_WHITE):
    """
    This function draws 2D text on the screen. It's used for the HUD.
    It works by temporarily switching to a 2D orthographic view.
    """
    glColor3f(*color) # Set the text color
    glMatrixMode(GL_PROJECTION)
    glPushMatrix() # Save the current projection matrix
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT) # Set up a 2D coordinate system

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix() # Save the current modelview matrix
    glLoadIdentity()

    glRasterPos2f(x, y) # Position the text
    for char in text:
        glutBitmapCharacter(font, ord(char)) # Draw each character

    glPopMatrix() # Restore the original modelview matrix
    glMatrixMode(GL_PROJECTION)
    glPopMatrix() # Restore the original projection matrix
    glMatrixMode(GL_MODELVIEW)

def draw_cylinder(pos, radius, height, color):
    """A helper function to draw a simple cylinder."""
    glPushMatrix()
    glColor3f(*color)
    glTranslatef(pos[0], pos[1], pos[2])
    glRotatef(-90, 1, 0, 0) # Rotate to make it stand upright (along Y-axis)
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, 20, 20)
    # Draw a cap on top
    glTranslatef(0,0,height)
    gluDisk(quad, 0, radius, 20, 1)
    glPopMatrix()

### D2. Arena and Environment Drawing ###

def draw_arena():
    """Draws the checkerboard floor and the four colored boundary walls."""
    # Draw the Floor
    glPushMatrix()
    num_tiles = ARENA_SIZE // TILE_SIZE
    for i in range(-num_tiles, num_tiles):
        for j in range(-num_tiles, num_tiles):
            # Alternate colors for the checkerboard effect
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

    # Draw the Walls
    wall_height = 100
    glPushMatrix()
    # Wall 1 (Positive Z)
    glColor3f(*COLOR_RED)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, ARENA_SIZE); glEnd()
    # Wall 2 (Negative Z)
    glColor3f(*COLOR_GREEN)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, -ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    # Wall 3 (Positive X)
    glColor3f(*COLOR_BLUE)
    glBegin(GL_QUADS); glVertex3f(ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    # Wall 4 (Negative X)
    glColor3f(*COLOR_YELLOW)
    glBegin(GL_QUADS); glVertex3f(-ARENA_SIZE, 0, -ARENA_SIZE); glVertex3f(-ARENA_SIZE, 0, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, ARENA_SIZE); glVertex3f(-ARENA_SIZE, wall_height, -ARENA_SIZE); glEnd()
    glPopMatrix()

    # Draw Special Tiles
    for tile in special_tiles:
        x, z, tile_type = tile['pos'][0], tile['pos'][2], tile['type']
        color = COLOR_BLACK if tile_type == 'sticky' else COLOR_GRAY
        glColor4f(color[0], color[1], color[2], 0.8) # Use alpha for transparency
        glPushMatrix()
        glTranslatef(0, 1, 0) # Draw slightly above the floor to avoid z-fighting
        glBegin(GL_QUADS)
        glVertex3f(x, 0, z); glVertex3f(x+TILE_SIZE, 0, z); glVertex3f(x+TILE_SIZE, 0, z+TILE_SIZE); glVertex3f(x, 0, z+TILE_SIZE);
        glEnd()
        glPopMatrix()


### D3. Game Object Drawing ###

def draw_player():
    """Draws the player character as a composite object."""
    glPushMatrix()
    # Apply player's position and rotation to the model matrix
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0, 1, 0)

    # Body (Cube)
    glColor3f(0.2, 0.4, 0.8)
    glPushMatrix(); glScalef(1, 1.5, 0.8); glutSolidCube(20); glPopMatrix()

    # Head (Sphere)
    glColor3f(0.8, 0.6, 0.4)
    glPushMatrix(); glTranslatef(0, 25, 0); glutSolidSphere(10, 20, 20); glPopMatrix()

    # "Nose" to indicate direction
    glColor3f(1, 1, 1)
    glPushMatrix(); glTranslatef(0, 15, -10); glutSolidCube(5); glPopMatrix()

    # If carrying a package, draw it
    if is_carrying_package:
        glColor3f(*carried_package_info['color'])
        glPushMatrix(); glTranslatef(20, 10, 0); glutSolidCube(10); glPopMatrix()

    glPopMatrix()

#-------------------------------------------------------------------------------------------
def clamp_player_inside_arena(old_x, old_z):
    """
    Keep player within an inner rectangle:
      x ∈ [-(ARENA_SIZE - margin_x), +(ARENA_SIZE - margin_x)]
      z ∈ [-(ARENA_SIZE - margin_z), +(ARENA_SIZE - margin_z)]
    If only one axis violates, we revert just that axis (nice wall sliding).
    """
    inner_x = ARENA_SIZE - PLAYER_BOUND_MARGIN_X
    inner_z = ARENA_SIZE - PLAYER_BOUND_MARGIN_Z

    # X axis
    if player_pos[0] >  inner_x: player_pos[0] = inner_x
    if player_pos[0] < -inner_x: player_pos[0] = -inner_x

    # Z axis
    if player_pos[2] >  inner_z: player_pos[2] = inner_z
    if player_pos[2] < -inner_z: player_pos[2] = -inner_z
#------------------------------------------------------------------------------------------


def draw_packages():
    """Draws all packages at the package station."""
    for pkg in packages:
        if not pkg['is_carried']:
            glPushMatrix()
            glTranslatef(pkg['pos'][0], pkg['pos'][1], pkg['pos'][2])
            glColor3f(*pkg['color'])
            glutSolidCube(15)
            # Tag on top
            glColor3f(1,1,1); glTranslatef(0,8,0); glutSolidCube(5)
            glPopMatrix()

def draw_beacons():
    """Draws the route beacons, highlighting the current one."""
    for i, beacon in enumerate(route_beacons):
        is_current = (i == current_beacon_index)
        base_color = beacon['color']

        # The current beacon glows, others are dim. The final drop zone is white.
        if i == len(route_beacons) - 1: # Drop Zone
            color = COLOR_WHITE
        elif is_current:
            # Make the current beacon "glow" by oscillating its brightness
            brightness = 0.6 + 0.4 * (math.sin(game_time * 5) + 1) / 2
            color = (base_color[0]*brightness, base_color[1]*brightness, base_color[2]*brightness)
        else: # Inactive beacon
             color = (base_color[0]*0.2, base_color[1]*0.2, base_color[2]*0.2)

        draw_cylinder(beacon['pos'], 10, 100, color)


### D4. Hazards and Collectibles Drawing ###

def draw_hazards():
    """Draws dynamic hazards like spikes and gates."""
    # Draw Spikes
    for spike in spikes:
        draw_cylinder(spike['pos'], 10, spike['current_height'], COLOR_GRAY)

    # Draw Gates
    for gate in gates:
        glPushMatrix()
        glTranslatef(gate['pos'][0], gate['current_height'], gate['pos'][2])
        glScalef(gate['scale'][0], gate['scale'][1], gate['scale'][2])
        glColor3f(0.3, 0.3, 0.3)
        glutSolidCube(1)
        glPopMatrix()

def draw_bonus_rings():
    """Draws floating bonus rings."""
    for ring in bonus_rings:
        glPushMatrix()
        glTranslatef(ring['pos'][0], ring['pos'][1], ring['pos'][2])
        glColor3f(*COLOR_YELLOW)
        # A ring is a circle of small spheres
        for i in range(20):
            angle = math.radians(i * 18)
            x = ring['radius'] * math.cos(angle)
            z = ring['radius'] * math.sin(angle)
            glPushMatrix()
            glTranslatef(x, 0, z)
            glutSolidSphere(3, 10, 10)
            glPopMatrix()
        glPopMatrix()


### D5. HUD Drawing ###
def draw_hud():
    """Draws the Heads-Up Display with all game information."""
    # Time
    draw_text(10, WINDOW_HEIGHT - 30, f"Time Left: {int(time_left)}")

    # Score
    draw_text(10, WINDOW_HEIGHT - 60, f"Score: {total_score}")

    # Package Status
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

    # Checkpoint
    draw_text(200, WINDOW_HEIGHT - 60, f"Next Beacon: {current_beacon_index + 1} / {len(route_beacons)}")

    # Stamina Bar
    draw_text(10, 50, "Stamina")
    # Bar Background
    glColor3f(0.2, 0.2, 0.2); glBegin(GL_QUADS); glVertex2f(10, 20); glVertex2f(210, 20); glVertex2f(210, 40); glVertex2f(10, 40); glEnd()
    # Bar Foreground
    stamina_width = 200 * (stamina / STAMINA_MAX)
    glColor3f(0, 0.8, 0); glBegin(GL_QUADS); glVertex2f(10, 20); glVertex2f(10 + stamina_width, 20); glVertex2f(10 + stamina_width, 40); glVertex2f(10, 40); glEnd()

    # Combo Meter
    if clean_turn_combo > 0:
        draw_text(WINDOW_WIDTH - 150, 50, f"Combo: {clean_turn_combo}x", color=COLOR_YELLOW)

    # Pause message
    if game_state == 'paused':
        draw_text(WINDOW_WIDTH/2 - 50, WINDOW_HEIGHT/2, "PAUSED", font=GLUT_BITMAP_TIMES_ROMAN_24)

    # Draw HUD arrow pointing to the next beacon
    if len(route_beacons) > 0 and current_beacon_index < len(route_beacons):
        target_pos = route_beacons[current_beacon_index]['pos']
        # Vector from player to target
        dx = target_pos[0] - player_pos[0]
        dz = target_pos[2] - player_pos[2]
        # Angle of the target relative to the world's Z-axis
        target_angle_world = math.degrees(math.atan2(dx, dz))
        # Angle to draw on HUD is relative to player's view
        arrow_angle = target_angle_world - player_angle

        glPushMatrix()
        # Position arrow in the top-center of the screen
        glTranslatef(WINDOW_WIDTH / 2, WINDOW_HEIGHT - 50, 0)
        glRotatef(-arrow_angle, 0, 0, 1) # Rotate the arrow
        glColor3f(*COLOR_YELLOW)
        glBegin(GL_TRIANGLES)
        glVertex2f(0, 15); glVertex2f(-10, -10); glVertex2f(10, -10)
        glEnd()
        glPopMatrix()


# --- E. GAME LOGIC AND UPDATE FUNCTIONS ---

def get_distance(p1, p2):
    """Calculates the 2D distance between two points [x, y, z]."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[2] - p2[2])**2)

def start_new_delivery():
    """Resets and randomizes the game for a new delivery run."""
    global route_color, current_beacon_index, packages, route_beacons, bonus_rings, special_tiles
    
    # 1. Reset route state
    current_beacon_index = 0
    route_beacons.clear()
    packages.clear()
    bonus_rings.clear()
    special_tiles.clear()

    # 2. Pick a new route color (different from the last one)
    old_color = route_color
    while route_color == old_color:
        route_color = random.choice(ROUTE_COLORS)

    # 3. Generate new beacon positions
    for i in range(4): # 4 beacons
        pos = [random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50), 0, random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50)]
        route_beacons.append({'pos': pos, 'color': route_color})
    # Add final drop zone
    pos = [random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50), 0, random.uniform(-ARENA_SIZE+50, ARENA_SIZE-50)]
    route_beacons.append({'pos': pos, 'color': COLOR_WHITE})

    # 4. Generate packages at the station (around -300, 0, -300)
    correct_pkg_pos = [random.uniform(-350, -250), 7.5, random.uniform(-350, -250)]
    packages.append({'pos': correct_pkg_pos, 'color': route_color, 'is_correct': True, 'is_carried': False})
    # Generate 2-3 decoy packages
    decoy_colors = [c for c in ROUTE_COLORS if c != route_color]
    for i in range(random.randint(2,3)):
        pos = [random.uniform(-350, -250), 7.5, random.uniform(-350, -250)]
        packages.append({'pos': pos, 'color': random.choice(decoy_colors), 'is_correct': False, 'is_carried': False})
        
    # 5. Generate a few bonus rings and special tiles
    for i in range(random.randint(3,5)):
        pos = [random.uniform(-ARENA_SIZE, ARENA_SIZE), 60, random.uniform(-ARENA_SIZE, ARENA_SIZE)]
        bonus_rings.append({'pos': pos, 'radius': 30})
    for i in range(5):
        x = random.randint(-8, 7) * TILE_SIZE
        z = random.randint(-8, 7) * TILE_SIZE
        special_tiles.append({'pos': [x,0,z], 'type': 'sticky'})



def Update_fixed_cam_from_orbit():
    """Recompute camera_pos_fixed.x/z from (radius, angle)."""
    rad = math.radians(cam_orbit_angle_deg)
    camera_pos_fixed[0] = cam_orbit_radius * math.sin(rad)   # x = r * sin(theta)
    camera_pos_fixed[2] = cam_orbit_radius * math.cos(rad)   # z = r * cos(theta)

#----------------------------------------------------------------------------------
def Compute_follow_targets():
    """Return (eye_xyz, ctr_xyz) for the OTS follow camera based on player pose."""
    rad = math.radians(player_angle)
    fwdx, fwdz = math.sin(rad), math.cos(rad)         # forward on XZ
    rtx, rtz   = fwdz, -fwdx                          # right vector on XZ

    eye_x = player_pos[0] - fwdx*follow_back + rtx*follow_side
    eye_y = player_pos[1] + follow_up
    eye_z = player_pos[2] - fwdz*follow_back + rtz*follow_side

    ctr_x = player_pos[0] + fwdx*look_ahead
    ctr_y = player_pos[1] + follow_up*0.3
    ctr_z = player_pos[2] + fwdz*look_ahead
    return (eye_x, eye_y, eye_z), (ctr_x, ctr_y, ctr_z)


#----------------------------------------------------------------------------------


def init_game():
    """Initializes or resets the entire game to its starting state."""
    global game_state, time_left, total_score, player_pos, player_angle, stamina
    global last_frame_time, game_time, completed_deliveries, is_carrying_package, carried_package_info
    
    print("Initializing new game...")
    game_state = 'playing'
    time_left = 156.0
    total_score = 0
    completed_deliveries = 0
    player_pos = [0.0, 15.0, 0.0]
    player_angle = 0.0
    stamina = STAMINA_MAX
    is_carrying_package = False
    carried_package_info = None
    
    # Initialize hazards (spikes and gates)
    spikes.clear()
    gates.clear()
    for i in range(5):
        pos = [random.uniform(-ARENA_SIZE, ARENA_SIZE), 0, random.uniform(-ARENA_SIZE, ARENA_SIZE)]
        spikes.append({'pos': pos, 'current_height': 0})
    
    gate_pos = [100, 0, 0]
    gates.append({'pos': gate_pos, 'current_height': 0, 'scale': [20, 100, 150]})

    start_new_delivery() # Set up the first delivery
    last_frame_time = time.time()
    game_time = 0.0

#------------------------------------------------------------------------------------------------------
def clamp_player_inside_arena(old_x, old_z):
    inner_x = ARENA_SIZE - PLAYER_BOUND_MARGIN_X
    inner_z = ARENA_SIZE - PLAYER_BOUND_MARGIN_Z
    if player_pos[0] >  inner_x: player_pos[0] = inner_x
    if player_pos[0] < -inner_x: player_pos[0] = -inner_x
    if player_pos[2] >  inner_z: player_pos[2] = inner_z
    if player_pos[2] < -inner_z: player_pos[2] = -inner_z
#------------------------------------------------------------------------------------------------------

def update_player(delta_time):
    """Updates player position, rotation, and stamina based on input."""
    global player_pos, player_angle, player_speed, stamina, clean_turn_combo, last_turn_time

    # --- Sprinting and Stamina ---
    is_sprinting = key_states.get(b'shift', False) and stamina > 0
    if is_sprinting:
        player_speed = PLAYER_SPEED_SPRINT
        stamina -= STAMINA_DRAIN_RATE * delta_time
    else:
        player_speed = PLAYER_SPEED_NORMAL
        if stamina < STAMINA_MAX:
            stamina += STAMINA_REGEN_RATE * delta_time
    stamina = max(0, min(stamina, STAMINA_MAX)) # Clamp stamina between 0 and MAX

    # --- Rotation ---
    is_turning = False
    if key_states.get(b'a', False):
        player_angle -= PLAYER_ROTATION_SPEED * delta_time
        is_turning = True
    if key_states.get(b'd', False):
        player_angle += PLAYER_ROTATION_SPEED * delta_time
        is_turning = True

#====================================================================================
    # --- Forward/Backward Movement (REPLACE your old block with THIS) ---
    move_dir = 0
    if key_states.get(b'w', False):
        move_dir = 1
    if key_states.get(b's', False):
        move_dir = -1

    # Save previous position (used for clean wall handling / clamping)
    old_x, old_z = player_pos[0], player_pos[2]

    if move_dir != 0:
        angle_rad = math.radians(player_angle)
        dx = math.sin(angle_rad) * player_speed * delta_time
        dz = math.cos(angle_rad) * player_speed * delta_time
        player_pos[0] += dx * move_dir
        player_pos[2] += dz * move_dir
#====================================================================================

    # --- Combo Logic ---
    if is_turning and move_dir == 1: # If moving forward and turning
        if time.time() - last_turn_time < 1.0: # Check if the last turn was recent
            clean_turn_combo += 1
            last_turn_time = time.time()
    else: # If not turning or moving, reset combo after a delay
        if time.time() - last_turn_time > 1.5:
            clean_turn_combo = 0
    
    if is_turning and move_dir == 1:
        last_turn_time = time.time()


    # --- Arena Boundary Collision (REPLACE your old two clamp lines) ---
    clamp_player_inside_arena(old_x, old_z)


def update_hazards(delta_time):
    """Animates spikes and gates."""
    # Update spike heights using a sine wave for smooth animation
    for spike in spikes:
        # Each spike can have a random offset to desynchronize them
        offset = spike['pos'][0] 
        spike['current_height'] = 30 * (math.sin(game_time * 2 + offset) + 1)

    # Update gate positions
    for gate in gates:
        gate['current_height'] = 50 * (math.sin(game_time * 0.5) + 1)


def handle_collisions_and_interactions(delta_time):
    """Manages all game interactions: pickups, beacon checks, hazard collisions."""
    global time_left, total_score, is_carrying_package, carried_package_info, current_beacon_index, completed_deliveries

    # 1. Package Pickup/Drop Logic
    if key_states.get(b'u', False): # Pick up
        if not is_carrying_package:
            for pkg in packages:
                if get_distance(player_pos, pkg['pos']) < 30:
                    is_carrying_package = True
                    carried_package_info = pkg
                    pkg['is_carried'] = True
                    if not pkg['is_correct']:
                        time_left -= 5 # Penalty for wrong package
                    break # Only pick up one
        key_states[b'u'] = False # Consume the key press
    
    if key_states.get(b'f', False): # Drop
        if is_carrying_package:
            carried_package_info['is_carried'] = False
            # Drop it at the player's feet
            carried_package_info['pos'] = list(player_pos)
            is_carrying_package = False
            carried_package_info = None
        key_states[b'f'] = False

    # 2. Beacon Check Logic
    if current_beacon_index < len(route_beacons):
        target_beacon = route_beacons[current_beacon_index]
        if get_distance(player_pos, target_beacon['pos']) < 30:
            if is_carrying_package and carried_package_info['is_correct']:
                # Reached the final drop zone
                if current_beacon_index == len(route_beacons) - 1:
                    total_score += 100
                    time_left += 10
                    completed_deliveries += 1
                    is_carrying_package = False # Drop package automatically
                    carried_package_info['is_carried'] = False
                    start_new_delivery()
                else: # Reached a normal beacon
                    total_score += 20
                    current_beacon_index += 1

    # 3. Hazard Collisions
    # Spikes
    for spike in spikes:
        if spike['current_height'] > 10 and get_distance(player_pos, spike['pos']) < PLAYER_RADIUS + 10:
            time_left -= 0.1 # Small continuous damage/penalty
            # Optional: Add knockback here

    # 4. Bonus Ring Collection
    for ring in bonus_rings[:]: # Iterate over a copy to allow removal
        if get_distance(player_pos, ring['pos']) < ring['radius']:
            time_left += 5
            total_score += 10
            bonus_rings.remove(ring)

    # 5. Special Tiles
    on_sticky_tile = False
    for tile in special_tiles:
        if tile['type'] == 'sticky':
            x, z = tile['pos'][0], tile['pos'][2]
            if x < player_pos[0] < x + TILE_SIZE and z < player_pos[2] < z + TILE_SIZE:
                on_sticky_tile = True
                break
    if on_sticky_tile:
        # Halve the current speed
        global player_speed
        player_speed /= 2


def update_game(delta_time):
    """The main update function, called every frame from idle()."""
    global time_left, game_state, game_time
    
    game_time += delta_time # Increment global animation timer

    # Update all game components
    update_player(delta_time)
    update_hazards(delta_time)
    handle_collisions_and_interactions(delta_time)

    # Update main timer and check for failure
    time_left -= delta_time
    if time_left <= 0:
        time_left = 0
        game_state = 'fail'
        print("Game Over! You ran out of time.")

# --- F. GLUT CALLBACK FUNCTIONS ---

def keyboardListener(key, x, y):
    """Handles key down events."""
    global game_state
    key_states[key.lower()] = True # Store that the key is being pressed
    key_states[b'shift'] = glutGetModifiers() & GLUT_ACTIVE_SHIFT

    # Handle single-press actions like pause and reset
    if key == b'p' or key == b'P':
        game_state = 'paused' if game_state == 'playing' else 'playing'
    if key == b'r' or key == b'R':
        init_game() # Reset the game

def keyboardUpListener(key, x, y):
    """Handles key up events."""
    key_states[key.lower()] = False # Store that the key is released
    key_states[b'shift'] = glutGetModifiers() & GLUT_ACTIVE_SHIFT

#----------------------------------------------------------------------------------------

# def specialKeyListener(key, x, y):

#     if camera_mode_is_follow:
#         # Do nothing in follow mode for now (easy to extend later if you want).
#         return

#     # --- tuning steps ---
#     STEP_Y   = 30.0   # height change per key press
#     STEP_ANG = 3.0    # degrees per key press

#     # --- height (Y) ---
#     if key == GLUT_KEY_UP:
#         camera_pos_fixed[1] += STEP_Y
#     if key == GLUT_KEY_DOWN:
#         camera_pos_fixed[1] -= STEP_Y

#     # Clamp height to sensible bounds
#     camera_pos_fixed[1] = max(60.0, min(1500.0, camera_pos_fixed[1]))

#     # --- orbit (LEFT/RIGHT) ---
#     if key == GLUT_KEY_LEFT:
#         cam_orbit_angle_deg += STEP_ANG           # rotate counter-clockwise
#     if key == GLUT_KEY_RIGHT:
#         cam_orbit_angle_deg -= STEP_ANG           # rotate clockwise

#     # Recompute X/Z from (radius, angle)
#     Update_fixed_cam_from_orbit()

#     # Ask GLUT to redraw with the new camera
#     glutPostRedisplay()


def specialKeyListener(key, x, y):
    """
    Arrow keys:
      FIXED camera  : UP/DOWN = height, LEFT/RIGHT = orbit around arena center
      FOLLOW (OTS)  : UP/DOWN = nudge camera up/down, LEFT/RIGHT = shoulder peek
    """
    global camera_pos_fixed, cam_orbit_angle_deg, cam_orbit_radius
    global follow_up, follow_side

    if camera_mode_is_follow:
        # --- OTS follow tweaks ---
        STEP_UP   = 2.5     # vertical nudge
        STEP_SIDE = 2.5     # shoulder nudge
        if key == GLUT_KEY_UP:    follow_up  += STEP_UP
        if key == GLUT_KEY_DOWN:  follow_up  -= STEP_UP
        if key == GLUT_KEY_LEFT:  follow_side -= STEP_SIDE
        if key == GLUT_KEY_RIGHT: follow_side += STEP_SIDE
        # keep within sensible bounds
        follow_up  = max(10.0, min(120.0, follow_up))
        follow_side = max(-50.0, min(50.0, follow_side))
    else:
        # --- fixed camera control ---
        STEP_Y   = 30.0     # height change
        STEP_ANG = 3.0      # orbit degrees per press
        if key == GLUT_KEY_UP:    camera_pos_fixed[1] += STEP_Y
        if key == GLUT_KEY_DOWN:  camera_pos_fixed[1] -= STEP_Y
        camera_pos_fixed[1] = max(60.0, min(1500.0, camera_pos_fixed[1]))
        if key == GLUT_KEY_LEFT:  cam_orbit_angle_deg += STEP_ANG
        if key == GLUT_KEY_RIGHT: cam_orbit_angle_deg -= STEP_ANG
        Update_fixed_cam_from_orbit()

    glutPostRedisplay()


#------------------------------------------------------------------------------------------


def mouseListener(button, state, x, y):
    """Handles mouse clicks."""
    global camera_mode_is_follow, follow_eye, follow_ctr
    # Right mouse button toggles camera tracking mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode_is_follow = not camera_mode_is_follow       # toggle mode
        if camera_mode_is_follow:
            # snap the smoothed camera to the target on entry (no pop)
            tgt_eye, tgt_ctr = Compute_follow_targets()
            follow_eye[:] = list(tgt_eye)
            follow_ctr[:] = list(tgt_ctr)
        glutPostRedisplay()
#------------------------------------------------------------------------------------------

# def setupCamera():
    
#     if camera_mode_is_follow:
#         # Follow Cam: Position camera behind and above the player
#         angle_rad = math.radians(player_angle)
#         # Calculate camera position based on player's angle
#         cam_x = player_pos[0] - 100 * math.sin(angle_rad)
#         cam_y = player_pos[1] + 60
#         cam_z = player_pos[2] - 100 * math.cos(angle_rad)
#         # Look from the calculated position towards the player
#         gluLookAt(cam_x, cam_y, cam_z,   # Camera Position
#                   player_pos[0], player_pos[1] + 15, player_pos[2], # Look At Target (slightly above player)
#                   0, 1, 0) # Up Vector (Y is up)
#     else:
#         # Fixed Cam: Static overview of the arena
#         gluLookAt(camera_pos_fixed[0], camera_pos_fixed[1], camera_pos_fixed[2],
#                   0, 0, 0, # Look at the center of the arena
#                   0, 1, 0) # Up Vector (Y is up)
        
def setupCamera():
    """Configures the camera's projection and view settings."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, (WINDOW_WIDTH / WINDOW_HEIGHT), 0.1, 2000.0)  # keep your FOV

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode_is_follow:
        # Over-the-shoulder: smoothly move toward the target each frame
        tgt_eye, tgt_ctr = Compute_follow_targets()
        s = follow_smooth
        for i in range(3):
            follow_eye[i] = follow_eye[i]*(1.0 - s) + tgt_eye[i]*s
            follow_ctr[i] = follow_ctr[i]*(1.0 - s) + tgt_ctr[i]*s

        gluLookAt(follow_eye[0], follow_eye[1], follow_eye[2],
                  follow_ctr[0], follow_ctr[1], follow_ctr[2],
                  0, 1, 0)
    else:
        # Fixed camera: orbit/height controlled by arrow keys
        gluLookAt(camera_pos_fixed[0], camera_pos_fixed[1], camera_pos_fixed[2],
                  0, 0, 0,
                  0, 1, 0)



def idle():
    """
    The main game loop, called continuously by GLUT.
    It calculates delta_time for frame-rate independent physics and logic.
    """
    global last_frame_time
    
    # Calculate time since the last frame
    current_time = time.time()
    delta_time = current_time - last_frame_time
    last_frame_time = current_time

    # If the game is not paused, update all game logic
    if game_state == 'playing':
        update_game(delta_time)

    # Trigger a redraw of the screen
    glutPostRedisplay()


def showScreen():
    """The main display function, responsible for all rendering."""
    # 1. Clear the screen
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST) # Ensure 3D objects occlude each other correctly
    glEnable(GL_BLEND) # Enable blending for transparent tiles
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # 2. Set up the camera
    setupCamera()

    # 3. Draw all 3D game elements
    draw_arena()
    draw_player()
    draw_packages()
    draw_beacons()
    draw_hazards()
    draw_bonus_rings()

    # 4. Draw the 2D HUD on top of everything
    # We must disable depth test for this so it's always visible
    glDisable(GL_DEPTH_TEST)
    draw_hud()
    glEnable(GL_DEPTH_TEST)

    # 5. Swap buffers to display the newly drawn frame
    glutSwapBuffers()


# --- G. MAIN FUNCTION ---
def main():
    """Initializes GLUT and starts the main application loop."""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Courier Run 3D")

    # Register all the callback functions
    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener) # IMPORTANT for smooth movement
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    init_game() # Set up the initial game state

    print("--- Controls ---")
    print("W/S: Move Forward/Backward")
    print("A/D: Rotate Left/Right")
    print("Shift: Sprint")
    print("U: Pick Up Package")
    print("F: Drop Package")
    print("Right Mouse Click: Toggle Camera Mode")
    print("P: Pause Game")
    print("R: Reset Game")
    
    glutMainLoop()

if __name__ == "__main__":
    main()