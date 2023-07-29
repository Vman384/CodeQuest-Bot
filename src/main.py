"""
This is your starting point for a Python bot. It will read and store the game information every turn, then responds
with an action. For now, this action is just shooting with a random angle. Write your own logic in game.py.
"""

from game import Game
from object_types import ObjectTypes
import math 

class Shoot:
    def __init__(self) -> None:
        #game = Game()
        self.x1,self.y1 = game.objects[game.other_tank_id["position"]][0], game.objects[game.other_tank_id["position"]][1]
        self.x2,self.y2 = game.objects[game.tank_id["position"]][0], game.objects[game.tank_id["position"]][1]
        self.angle = 0
    
    def other_tank_angle(self,x1,y1,x2,y2):
        dx = x2 - x1
        dy = y2 - y1
        angle = math.atan2(dy, dx)  # returns angle in radians
        angle = math.degrees(angle)  # convert to degrees
        self.angle = angle 

if __name__ == "__main__":
    game = Game()
    while game.read_next_turn_data():
        game.respond_to_turn()
