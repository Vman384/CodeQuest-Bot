import random

import comms
from object_types import ObjectTypes
import sys
import math


class Game:
    """
    Stores all information about the game and manages the communication cycle.
    Available attributes after initialization will be:
    - tank_id: your tank id
    - objects: a dict of all objects on the map like {object-id: object-dict}.
    - width: the width of the map as a floating point number.
    - height: the height of the map as a floating point number.
    - current_turn_message: a copy of the message received this turn. It will be updated everytime `read_next_turn_data`
        is called and will be available to be used in `respond_to_turn` if needed.
    """
    def __init__(self):
        tank_id_message: dict = comms.read_message()
        self.tank_id = tank_id_message["message"]["your-tank-id"]
        self.other_tank_id = tank_id_message["message"]["enemy-tank-id"]
        #previous position of the other tank
        self.previous_position = []
        self.current_turn_message = None
        self.wall_in_path = False

        # We will store all game objects here
        self.objects = {}

        next_init_message = comms.read_message()
        while next_init_message != comms.END_INIT_SIGNAL:
            # At this stage, there won't be any "events" in the message. So we only care about the object_info.
            object_info: dict = next_init_message["message"]["updated_objects"]

            # Store them in the objects dict
            self.objects.update(object_info)

            # Read the next message
            next_init_message = comms.read_message()

        # We are outside the loop, which means we must've received the END_INIT signal

        # Let's figure out the map size based on the given boundaries

        # Read all the objects and find the boundary objects
        boundaries = []
        self.walls = set()
        self.destrucable_walls = set()
        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.BOUNDARY.value:
                boundaries.append(game_object)
            elif game_object['type'] == ObjectTypes.WALL.value:
                self.walls.add(tuple(game_object['position']))
            elif game_object['type'] == ObjectTypes.DESTRUCTIBLE_WALL.value:
                self.destrucable_walls.add(tuple(game_object['position']))
            elif game_object['type'] == ObjectTypes.CLOSING_BOUNDARY.value:
                self.closing_boundary = game_object['position']



        # The biggest X and the biggest Y among all Xs and Ys of boundaries must be the top right corner of the map.

        # Let's find them. This might seem complicated, but you will learn about its details in the tech workshop.
        biggest_x, biggest_y = [
            max([max(map(lambda single_position: single_position[i], boundary["position"])) for boundary in boundaries])
            for i in range(2)
        ]

        self.width = biggest_x
        self.height = biggest_y
        

    def read_next_turn_data(self):
        """
        It's our turn! Read what the game has sent us and update the game info.
        :returns True if the game continues, False if the end game signal is received and the bot should be terminated
        """
        # Read and save the message
        self.current_turn_message = comms.read_message()

        if self.current_turn_message == comms.END_SIGNAL:
            return False

        # Delete the objects that have been deleted
        # NOTE: You might want to do some additional logic here. For example check if a powerup you were moving towards
        # is already deleted, etc.
        for deleted_object_id in self.current_turn_message["message"]["deleted_objects"]:
            try:
                del self.objects[deleted_object_id]
                self.powerups.remove(deleted_object_id)
                self.bullets.remove(deleted_object_id)
            except KeyError:
                pass

        # Update your records of the new and updated objects in the game
        # NOTE: you might want to do some additional logic here. For example check if a new bullet has been shot or a
        # new powerup is now spawned, etc.
        self.objects.update(self.current_turn_message["message"]["updated_objects"])
        self.bullets = set()
        self.powerups = set()
        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.BULLET.value:
                self.bullets.add(tuple(game_object['position']))
            elif game_object['type'] == ObjectTypes.POWERUP.value:
                self.powerups.add(tuple(game_object['position'])) 

        return True

    def other_tank_angle(self):
        self.x1, self.y1 = self.objects[self.other_tank_id]["position"][0], self.objects[self.other_tank_id]["position"][1]
        x2, y2 = self.objects[self.tank_id]["position"][0], self.objects[self.tank_id]["position"][1]
        dx = self.x1 - x2
        dy = self.y1 - y2
        angle = math.atan2(dy, dx)  # returns angle in radians
        angle = math.degrees(angle)  # convert to degrees

        if self.is_wall_in_path(x2, y2, angle):
            angle += 10

        return angle



    def is_wall_in_path(self, my_x, my_y, angle, wall_size=18, walls = None):
        if walls is None:
            walls = self.walls
        max_path = 100
        # Convert the angle to radians and get the direction vector
        angle_rad = math.radians(angle)
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)

        # Calculate the end point of the path
        end_x = my_x + dx * max_path # 1000 is an arbitrary large number
        end_y = my_y + dy * max_path

        # Check each wall
        for wall_x, wall_y in walls:
            # Calculate the corners of the wall
            half_size = wall_size / 2
            corners = [(wall_x - half_size, wall_y - half_size),
                    (wall_x + half_size, wall_y - half_size),
                    (wall_x + half_size, wall_y + half_size),
                    (wall_x - half_size, wall_y + half_size)]

            # Check each side of the wall
            for i in range(4):
                corner1 = corners[i]
                corner2 = corners[(i + 1) % 4]

                # Calculate the intersection of the path and the wall side
                denom = (corner1[0] - corner2[0]) * (my_y - end_y) - (corner1[1] - corner2[1]) * (my_x - end_x)
                if denom == 0:
                    continue  # The lines are parallel

                ua = ((corner1[0] - corner2[0]) * (my_y - corner1[1]) - (corner1[1] - corner2[1]) * (my_x - corner1[0])) / denom
                ub = ((my_x - end_x) * (my_y - corner1[1]) - (my_y - end_y) * (my_x - corner1[0])) / denom

                if 0 <= ua <= 1 and 0 <= ub <= 1:
                    return True  # There's an intersection

        # If no walls are in the path, return False
        return False 
    def move_tank(self):
        # Parameters
        spiral_radius = 100  # The radius of the spiral
        spiral_speed = 1.0  # The speed of the spiral movement
        randomness = 0.1  # The amount of randomness in the movement
        bullet_distance_threshold = 75

        # Get the current position of the tank
        x, y = self.objects[self.tank_id]["position"]

        # Calculate the center of the game area based on the positions of the border
        border_positions = self.closing_boundary
        self.center_x = sum(pos[0] for pos in border_positions) / len(border_positions)
        self.center_y = sum(pos[1] for pos in border_positions) / len(border_positions)

        # Calculate the current phase of the spiral based on the position of the tank
        phase = math.atan2(y - self.center_y, x - self.center_x)

        # Calculate the target position on the spiral
        target_x = self.center_x + spiral_radius * math.cos(phase + spiral_speed)
        target_y = self.center_y + spiral_radius * math.sin(phase + spiral_speed)

        # Calculate the angle to the target position
        dx = target_x - x
        dy = target_y - y
        target_angle = math.atan2(dy, dx)
        target_angle = math.degrees(target_angle)

        # Add some randomness to the target angle
        target_angle += random.uniform(-randomness, randomness)

        # Check if there's a wall in the path
        if self.is_wall_in_path(x, y, target_angle):
            self.wall_in_path = True
            if random.randint(0,2) == 1:
                self.wall_in_path = False
        else:
            self.wall_in_path = False
        if len(self.bullets)>0:
            for bullet in self.bullets:
                if abs(bullet[0] - x) < bullet_distance_threshold and abs(bullet[1] - y) < bullet_distance_threshold:
                    target_angle +=90
        return target_angle






    def respond_to_turn(self):
        """
        This is where you should write your bot code to process the data and respond to the game.
        """

        # Write your code here... For demonstration, this bot just shoots randomly every turn.

        if self.wall_in_path:
            comms.post_message({
                "shoot": self.other_tank_angle(),
                "path": [self.x1,self.y1]
            })
        else:
            comms.post_message({
                "shoot": self.other_tank_angle(),
                "move": self.move_tank()
            })


