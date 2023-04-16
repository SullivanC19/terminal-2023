import gamelib
import random
import math
import warnings
from sys import maxsize
import json

from typing import List, Dict, Tuple


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

attacker_range = 4.5
explosion_range = 9

class InterceptorPlan:
    def __init__(
            self,
            start_position: List[int],
            explode_position: List[int],
            extra_wall_positions: List[List[int]]):
        self.start_position = start_position
        self.explode_position = explode_position
        self.explode_time = 4 * (abs(start_position[0] - explode_position[0]) + abs(start_position[1] - explode_position[1]) + 1)
        self.extra_wall_positions = extra_wall_positions
        self.plan_side = start_position[0] <= 12

    def get_coverage_and_risk(
            self,
            enemy_attacker_position_percentage: Dict[List[int], float],
            game_state: gamelib.GameState) -> Tuple[float, List[List[int]], float]:
        
        positions_covered = []
        percentage_covered = 0.0
        percentage_risk = 0.0

        for attacker_position, percentage in enemy_attacker_position_percentage.items():
            attacker_path = game_state.find_path_to_edge(attacker_position)

            # attackers that finish their path before explosion are NOT covered
            if attacker_path is not None and len(attacker_path) < self.explode_time:
                continue

            # invalid spawn locations are covered
            # attackers that do not reach the edge are covered
            if attacker_path is None \
                or attacker_path[:-1] not in (game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)) \
                or game_state.game_map.distance_between_locations(self.explode_position, attacker_path[self.explode_time]) <= explosion_range:
                percentage_covered += percentage
                positions_covered.append(attacker_position)

            # consider risk of attackers that can hit unit before explosion
            if attacker_path is not None:
                for i in range(self.explode_time):
                    # check if unit gets in range of interceptor before explosion
                    if game_state.game_map.distance_between_locations(self.explode_position, attacker_path[i]) <= attacker_range:
                        percentage_risk += percentage
                        break

        return percentage_covered, positions_covered, percentage_risk
    
    def construct_interceptor_plan(self, game_state: gamelib.GameState):
        game_state.attempt_spawn(WALL, self.extra_wall_positions)
        game_state.attempt_remove(WALL, self.extra_wall_positions)
        game_state.attempt_spawn(INTERCEPTOR, self.start_position)

interceptor_plans = []

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

        self.starting_enemy_attacker_positions = dict()
        self.total_enemy_attacker_positions = 0

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        self.build_structures(game_state)
        self.build_mobile_units(game_state)
        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        print(state)

        enemy_attacker_positions = []
        # TODO check enemy attacker positions in first round

        for position in enemy_attacker_positions:
            if position not in self.starting_enemy_attacker_positions:
                self.starting_enemy_attacker_positions[position] = 0
            self.starting_enemy_attacker_positions[position] += 1

    def get_attacker_position_probabilities(self) -> Dict[List[int], float]:
        return {k: v / self.total_enemy_attacker_positions for k, v in self.starting_enemy_attacker_positions.items()}
    
    def spawn_interceptors(self, game_state: gamelib.GameState):
        if len(self.starting_enemy_attacker_positions) == 0:
            return

        def score(percentage_covered, percentage_risk, explode_time, num_new_walls_required) -> float:
            return percentage_covered - 0.5 * percentage_risk - explode_time * .001 - num_new_walls_required * .001
        
        attacker_probs = self.get_attacker_position_probabilities()

        total_coverage = 0.0
        left_side_plans = []
        right_side_plans = []
        while total_coverage < 0.9:
            best_plan = None
            best_plan_score = 0.0
            best_plan_coverage = 0.0
            best_plan_covered_positions = []
            for plan in interceptor_plans:
                percentage_covered, positions_covered, percentage_risk = plan.get_coverage_and_risk(attacker_probs, game_state)
                
                # make sure that plan does not change wall structure on its side
                shared_side_plans = left_side_plans if plan.plan_side else right_side_plans
                if len(shared_side_plans) > 0 and set(plan.extra_wall_positions) != set(shared_side_plans[0].extra_wall_positions):
                    continue

                num_new_walls_required = 0 if shared_side_plans else len(plan.extra_wall_positions)
                plan_score = score(percentage_covered, percentage_risk, plan.explode_time, num_new_walls_required)
                if plan_score > best_plan_score:
                    best_plan = plan
                    best_plan_score = plan_score
                    best_plan_coverage = percentage_covered
                    best_plan_covered_positions = positions_covered

            # prevent infinite loop
            if best_plan_coverage == 0:
                break

            for covered_position in best_plan_covered_positions:
                attacker_probs.pop(covered_position)

            if best_plan.plan_side:
                left_side_plans.append(best_plan)
            else:
                right_side_plans.append(best_plan)
        
            total_coverage += best_plan_coverage

        for plan in left_side_plans + right_side_plans:
            plan.construct_interceptor_plan(game_state)
        
    def build_structures(self, game_state: gamelib.GameState):
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

    def build_mobile_units(self, game_state: gamelib.GameState):
        self.spawn_interceptors(game_state)
        
        if game_state.turn_number % attack_rate == 0:
            attack_location = random.choice(attacker_locations)
            game_state.attempt_spawn(SCOUT, attack_location, num=1000)