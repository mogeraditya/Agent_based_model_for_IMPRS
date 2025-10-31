"""This module defines sound objects created"""

import math
import uuid

# from supporting_files.utilities import call_directionality_factor


class Sound:
    def __init__(
        self,
        parameters_df,
        origin,
        creation_time,
        emitter_id,
        direction_vector,
    ):
        self.parameters_df = parameters_df
        self.origin = origin
        self.creation_time = creation_time
        self.emitter_id = emitter_id
        self.initial_spl = self.parameters_df["EMITTED_SPL"][0]
        self.current_spl = self.parameters_df["EMITTED_SPL"][0]

        self.current_radius = 0.0
        self.speed = self.parameters_df["SOUND_SPEED"][0]
        # Keep track of when to kill sound; either when db is below 20 or when out of arena
        self.active = True
        self.id = uuid.uuid4()
        self.direction_vector = direction_vector

    def update(self, current_time):
        """Function to propagate sound with time.
        This function updates the radius of the sound disk with time.
        Also, ensures sounds outside the arena are "disabled" and no longer tracked.

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
        """
        elapsed = current_time - self.creation_time
        # print(elapsed, self.active)
        self.current_radius = self.speed * elapsed

        # Calculate spl with distance and air absorption

        if self.current_radius > 0:
            distance_effect = 20 * math.log10(self.current_radius / 1)
        
            self.current_spl = (
                self.initial_spl
                - distance_effect
                # - (self.parameters_df["AIR_ABSORPTION"][0] * self.current_radius)
            )
        # print(self.current_spl)
        if self.check_if_sound_outside_arena() and self.current_spl<self.parameters_df["MIN_DETECTABLE_SPL"][0]:
            self.active = False

    def contains_point(self, point):
        """Checks whether a given point is within the sound disk.

        Args:
            point (Vector): point to test.

        Returns:
            Bool: True if point inside sound object
        """
        distance = self.origin.distance_to(point)
        return distance <= self.current_radius and distance >= max(
            0, self.current_radius - self.parameters_df["SOUND_DISK_WIDTH"][0]
        )

    def __repr__(self):
        return (
            f"Sound(origin={self.origin}, radius={self.current_radius:.2f}, "
            f"spl={self.current_spl:.1f}dB, "
            f"emitter={self.emitter_id}, creation_time={self.creation_time}"
        )

    def check_if_sound_outside_arena(self):
        """Checks if sound is outside the bounds of the arena.
        Sound obejct is no longer tracked if its outside the arena.

        Returns:
            Bool: True if sound is outside the bounds of the arena, else False.
        """
        if (self.current_radius) > max(
            self.parameters_df["ARENA_HEIGHT"][0], self.parameters_df["ARENA_WIDTH"][0]
        ):

            return True
        else:
            return False

