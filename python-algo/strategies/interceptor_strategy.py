import gamelib
import random
import math
import warnings
from sys import maxsize
import json


interceptor_locations = [[7, 6], [20, 6]]
interceptor_wall_locations = [[6, 8], [6, 9], [6, 10], [7, 11], [8, 6], [8, 7], [8, 8], [8, 9], [8, 10],
                              [21, 8], [21, 9], [21, 10], [20, 11], [19, 6], [19, 7], [19, 8], [19, 9], [19, 10]]
interceptor_upgrade_wall_locations = [[7, 11], [20, 11]]

turret_locations = [[11, 10], [16, 10]]
turret_wall_location = [[11, 11], [16, 11]]
support_locations = [[9, 9], [18, 9], [10, 9], [17, 9], [11, 9], [16, 9], [12, 9], [15, 9],
                     [9, 8], [18, 8], [10, 8], [17, 8], [11, 8], [16, 8], [12, 8], [15, 8],
                     [9, 7], [18, 7], [10, 7], [17, 7], [11, 7], [16, 7], [12, 7], [15, 7],
                     [9, 6], [18, 6], [10, 6], [17, 6], [11, 6], [16, 6], [12, 6], [15, 6]]

attacker_locations = [[8, 5], [19, 5]]
attack_rate = 3

class InterceptorStrategy(gamelib.AlgoCore):
    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        self.build_structures(game_state)
        self.build_mobile_units(game_state)
        game_state.submit_turn()

    def build_structures(self, game_state):
        # Build interceptor ramp
        game_state.attempt_spawn(WALL, interceptor_wall_locations)
        game_state.attempt_upgrade(interceptor_upgrade_wall_locations)

        # Build turrets
        game_state.attempt_spawn(TURRET, turret_locations)
        game_state.attempt_spawn(WALL, turret_wall_location)
        game_state.attempt_upgrade(turret_wall_location)

        # Build and upgrade as many supports as we can
        for location in support_locations:
            game_state.attempt_spawn(SUPPORT, location)
            game_state.attempt_upgrade(location)

    def build_mobile_units(self, game_state):
        game_state.attempt_spawn(INTERCEPTOR, interceptor_locations)
        if game_state.turn_number % attack_rate == 0:
            attack_location = random.choice(attacker_locations)
            game_state.attempt_spawn(SCOUT, attack_location, num=1000)