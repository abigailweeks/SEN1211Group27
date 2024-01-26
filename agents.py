# Importing necessary libraries
import random
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage, \
    floodplain_multipolygon


# Define the Households agent class
class Households(Agent):
    """
    An agent representing a household in the model.
    Each household has a flood depth attribute which is randomly assigned for demonstration purposes.
    """
    adapted_friends_count: int

    def __init__(self, unique_id, model, friends_probability_factor, minimum_damage_loan_eligibility_factor, minimum_damage_grant_eligibility_factor, base_probability):
        super().__init__(unique_id, model)
        self.minimum_damage_loan_eligibility_factor = minimum_damage_loan_eligibility_factor
        self.minimum_damage_grant_eligibility_factor=minimum_damage_grant_eligibility_factor
        self.friends_probability_factor = friends_probability_factor
        self.base_probability=base_probability
        self.adapted_friends_count = 0
        self.is_adapted = False  # Initial adaptation status set to False
        self.is_eligible = False
        self.takes_loan = False
        self.takes_grant=False
        self.rank = 0

        # getting flood map values
        # Get a random location on the map
        loc_x, loc_y = generate_random_location_within_map_domain()
        self.location = Point(loc_x, loc_y)

        # Check whether the location is within floodplain
        self.in_floodplain = False
        if contains_xy(geom=floodplain_multipolygon, x=self.location.x, y=self.location.y):
            self.in_floodplain = True

        # Get the estimated flood depth at those coordinates. 
        # the estimated flood depth is calculated based on the flood map (i.e., past data) so this is not the actual flood depth
        # Flood depth can be negative if the location is at a high elevation
        self.flood_depth_estimated = get_flood_depth(corresponding_map=model.flood_map, location=self.location,
                                                     band=model.band_flood_img)
        # handle negative values of flood depth
        if self.flood_depth_estimated < 0:
            self.flood_depth_estimated = 0

        # calculate the estimated flood damage given the estimated flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_estimated = calculate_basic_flood_damage(flood_depth=self.flood_depth_estimated)

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0

        # calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual)

    # Function to count friends who can be influencial.
    def count_friends(self, radius):
        """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
        friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
        return len(friends)

    def count_friends_with_attribute(self):
        """Count the number of neighbors within a given radius with a specific attribute."""
        friends = self.model.grid.get_neighbors(self.pos, include_center=False)


        adapted_friends_count=0
        for friend in friends:
            if friend.is_adapted:
                adapted_friends_count += 1

        return adapted_friends_count

    def step(self):
        friends_probability_factor=self.friends_probability_factor
        minimum_damage_loan_eligibility_factor=self.minimum_damage_loan_eligibility_factor
        minimum_damage_grant_eligibility_factor=self.minimum_damage_grant_eligibility_factor

        # LOAN Logic for adaptation based on estimated flood damage and a random chance.
        if self.flood_damage_actual > minimum_damage_loan_eligibility_factor:
            self.is_eligible = True
        if self.is_eligible and self.model.government.gives_loan and self.count_friends_with_attribute()/self.friends_probability_factor + random.random()/self.base_probability > .2:
            self.takes_loan = True
        if self.takes_loan:
            self.is_adapted = True  # Agent adapts to flooding
        # GRANT logic for adaptation

        if self.flood_damage_actual >minimum_damage_grant_eligibility_factor and self.rank<=10 and self.model.government.gives_grant:
            self.takes_grant = True
        if self.takes_grant:
            self.is_adapted = True  # Agent adapts to flooding



# Define the Government agent class
class Government():
    """
    A government agent that currently doesn't perform any actions.
    """
    gives_loan = None
    gives_grant= None

    def __init__(self, model, grant_threshold, loan_threshold):
        self.gives_loan = False  # Initial loan status set to False
        self.gives_grant= False
        self.damage_threshold = loan_threshold
        self.grant_threshold= grant_threshold
        self.total_damage = 0
        self.model= model


    def sum_damage(self):
       self.total_damage = sum(
           [agent.flood_damage_actual for agent in self.model.schedule.agents if isinstance(agent, Households)])
       # The government agent doesn't perform any actions.
       if self.total_damage >= self.damage_threshold:
        self.gives_loan = True
       if self.total_damage>=self.grant_threshold:
        self.gives_grant=True


