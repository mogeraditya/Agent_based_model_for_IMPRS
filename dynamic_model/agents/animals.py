"""This module contains the code that describes a Animal object and its behaviours"""

import math
import random

import numpy as np
from agents.sounds import Sound
from supporting_files.utilities import call_directionality_factor, make_dir, make_vector
from supporting_files.vectors import Vector


class Animal:
    _id_counter = 0

    def __init__(self, parameters_df, output_dir):
        self.id = Animal._id_counter
        Animal._id_counter += 1

        self.parameters_df = parameters_df
        self.position = Vector(
            random.uniform(1, self.parameters_df["ARENA_WIDTH"][0] - 1),
            random.uniform(1, self.parameters_df["ARENA_HEIGHT"][0] - 1),
        )
        self.direction = Vector().random_direction()  # randomize start direction
        self.time_since_last_call = np.round(
            random.uniform(0, 1 / self.parameters_df["CALL_RATE"][0]), 3
        )
        self.emitted_sounds = []
        self.emit_times = [-np.inf]
        # Stores all received sounds;
        self.received_sounds = []
        # Stores all the position information.
        self.position_history = []
        # Clean up activates after every some steps to clear memory from RAM and store it on drive.
        self.time_since_last_cleanup = self.time_since_last_call
        self.output_dir = output_dir
        self.speed = self.parameters_df["Animal_BASE_SPEED"][0]
        self.radius = self.parameters_df["Animal_RADIUS"][0]

        self.detections_for_directon_change = []
        self.time_since_directon_change = -np.inf
        self.next_direction = self.direction
        
        self.activation_state = False # respond to sound or not
        self.destination = False
        
        if self.id==0:
            self.activation_state = True
            self.destination = Vector(0,0)

    def update(self, current_time, sound_objects):
        """Function to update Animals with time.
        This function handles movement update of Animal each time step.
        Also takes care of sound emission, detection of active sounds by the Animals.
        Animal detections over time is also cleared and stored locally.

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
            sound_objects (EchoSound): direct and echo sounds that are currently active.
        """
        current_time = np.round(current_time, 3)
        self.update_movement()
        self.position_history.append((current_time, (self.position.x, self.position.y)))

        if self.id == 0 :
            self.emit_sounds(current_time, sound_objects)
            self.activation_state = False
        elif self.id != 0  and self.activation_state == True:
            self.emit_sounds(current_time, sound_objects)
        # if self.id == 0 and self.time_since_directon_change == 0:
        #     print(current_time)

        # self.decide_next_direction(self.received_sounds)
        self.deactivate_once_goal_reached()
        self.update_directon(current_time, sound_objects)
        self.cleanup_sounds(current_time)
        self.detect_sounds(current_time, sound_objects)

    def update_movement(self):
        """Update poisition of Animal when called.
        Every timestep the position of the Animal needs to be
        updated based on velcoity and direction.
        """
        self.position += (
            self.direction * self.speed * self.parameters_df["TIME_STEP"][0]
        )

        # Boundary checks with bounce
        if (
            self.position.x <= 0
            or self.position.x >= self.parameters_df["ARENA_WIDTH"][0]
        ):
            self.direction.x *= -1
            self.next_direction = self.direction
        if (
            self.position.y <= 0
            or self.position.y >= self.parameters_df["ARENA_HEIGHT"][0]
        ):
            self.direction.y *= -1
            self.next_direction = self.direction

    def emit_sounds(self, current_time, sound_objects):
        """Trigger sound emission by Animal.
        Whenever the function is called, it checks if sufficient time
        has passed and a Sound Object is created.

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
            sound_objects (list): List containing all active sounds in the simulation
        """
        self.time_since_last_call += self.parameters_df["TIME_STEP"][0]
        call_interval = 1.0 / self.parameters_df["CALL_RATE"][0]

        if self.time_since_last_call >= call_interval:
            sound = Sound(
                parameters_df=self.parameters_df,
                origin=self.position,
                creation_time=current_time,
                emitter_id=self.id,
                direction_vector=self.direction,
            )
            self.emitted_sounds.append(sound)
            self.emit_times.append(current_time)
            sound_objects.append(sound)

            self.time_since_directon_change = 0
            self.time_since_last_call = np.random.uniform(-0.01, 0.01)
            self.time_since_last_cleanup = 0

    def given_sound_objects_return_detected(
        self, current_time, sound_objects, detect_self_call
    ):
        """given sounds generate list of sounds that a Animal can hear

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
            sound_objects (list): List containing all active sounds in the simulation
            detect_self_call (Bool): If true, add self call to detected, else, skip self call.

        Returns:
            list: sound detections given time.
        """
        array_of_sound_detections = []
        for sound in sound_objects:

            # if sound isnt active, i.e., outside arena or too quiet
            if not sound.active:
                continue

            # dont detect self call
            if (
                sound.emitter_id == self.id
                and isinstance(sound, Sound)
                and not detect_self_call
            ):
                continue
            # sound.update(current_time)

            # if sound cant be heard by Animal
            if sound.current_spl < self.parameters_df["MIN_DETECTABLE_SPL"][0]:
                # print(sound.current_spl)
                continue


            # sound can only be detected if Animal is inside the sound wave
            if sound.contains_point(self.position):

                # compute spl with call directionality, set A to directionality
                angle_between_sound_and_Animal = sound.direction_vector.angle_between(
                    self.position
                )
                call_directionality = call_directionality_factor(
                    A=0, theta=angle_between_sound_and_Animal
                )

                distance_between_sound_and_Animal = self.position.distance_to(sound.origin)
                # print(distance_between_sound_and_Animal)

                if distance_between_sound_and_Animal == 0:
                    spl_corrected_for_width = sound.initial_spl
                    # TODO: sounds near Animal will be loud af cause of log, fix?
                else:
                    distance_effect = 20 * math.log10(
                        distance_between_sound_and_Animal / 1
                    )
                    spl_corrected_for_width = (
                        sound.initial_spl
                        - distance_effect
                        # - (
                        #     self.parameters_df["AIR_ABSORPTION"][0]
                        #     * distance_between_sound_and_Animal
                        # )
                    )

                # store only necessary things of sound object
                incident_direction = sound.origin - self.position
                array_of_sound_detections.append(
                    {
                        "time": current_time,
                        "origin": (sound.origin.x, sound.origin.y),
                        "distance_from_Animal": sound.origin.distance_to(self.position),
                        "received_spl": spl_corrected_for_width + call_directionality,
                        "emitter_id": sound.emitter_id,
                        "sound_object_id": sound.id,
                        "sound_direction": (
                            sound.direction_vector.x,
                            sound.direction_vector.y,
                        ),
                        "incident_direction": (
                            incident_direction.x,
                            incident_direction.y,
                        ),
                        "Animal_direction": (self.direction.x, self.direction.y),
                        "Animal_position": (self.position.x, self.position.y),
                        "Animal_last_call_time": self.emit_times[-1],
                    }
                )
        return array_of_sound_detections

    def detect_sounds(self, current_time, sound_objects):
        """Detects sound that are audible to the Animal
        Checks if a Animal can hear a sound based on dbSpl of sound
        and position of Animal.

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
            sound_objects (list): _description_
        """
        self.received_sounds.extend(
            self.given_sound_objects_return_detected(
                current_time, sound_objects, detect_self_call=True
            )
        )

    def cleanup_sounds(self, current_time):
        """Stores the detections into a .npy file.
        After a fixed amount of time the detection list is stored
        into local memory and this is cleared from RAM.

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
        """
        # Keep only recent detections

        # if (current_time - self.time_since_last_cleanup) >= self.parameters_df[
        #     "CLEANUP_INTERVAL"
        # ][0] or np.round(
        #     self.time_since_last_cleanup, 3
        # ) == current_time:  # 10ms
        if self.time_since_last_cleanup == 0:
            dir_to_store = self.output_dir + "/" + str(self.id)
            make_dir(dir_to_store)
            np.save(
                dir_to_store
                + f"/Animal_{self.id}_received_sounds_snapshot_at_time_{current_time:.3f}.npy",
                self.received_sounds,
            )
            np.save(
                dir_to_store
                + f"/Animal_{self.id}_emitted_sounds_snapshot_at_time_{current_time:.3f}.npy",
                self.emitted_sounds,
            )
            self.time_since_last_cleanup = -np.inf  # current_time
            self.emitted_sounds = []
            self.received_sounds = []

    def get_detections_at_time(self, current_time):
        """

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.

        Returns:
            list: sounds that are detected by a Animal before a certain time.
        """
        return [d for d in self.received_sounds if d["time"] <= current_time]

    # inelligent movement
    def generate_random_direction(self):
        """assign a random direction to the Animal"""
        direction = self.direction
        if random.random() < self.parameters_df["PROPENSITY_TO_CHANGE_DIRECTION"][0]:
            direction = Vector().random_direction()
        return direction

    def generate_direction_vector_given_sound(self, sound):
        """generate direction vector of any sound

        Args:
            sound (EchoSound): sound to convert to vector

        Returns:
            Vector: Vector form of the input sound
        """
        spl_of_sound = sound["received_spl"]

        normalized_sound_vector = (
            Vector(x=sound["origin"][0], y=sound["origin"][1]) - self.position
        ).normalize()

        vector_w_spl_magnitude = normalized_sound_vector * spl_of_sound
        return vector_w_spl_magnitude

    def decide_next_direction(self, detected_sound_objects):
        """decide next direction of Animal based on sound

        Args:
            detected_sound_objects (list): list containing detected sounds
        """

        if len(detected_sound_objects) != 0:
            max_spl = np.max([i["received_spl"] for i in detected_sound_objects])

            if max_spl > 30:

                max_spl_sound = [
                    i for i in detected_sound_objects if i["received_spl"] == max_spl
                ][0]

                max_spl_sound_vector = self.generate_direction_vector_given_sound(
                    max_spl_sound
                )   
                next_direction = max_spl_sound_vector.normalize()
                scaling_based_intensity = ((max_spl - 30) / 5) 
                effect_strength = np.min([scaling_based_intensity, 15])
                self.speed = self.parameters_df["Animal_BASE_SPEED"][0]+ effect_strength      
                self.activation_state = True
                self.destination = make_vector(max_spl_sound["origin"])
            else:
                # Random direction change occasionally
                next_direction = self.generate_random_direction()
        else:
            # Random direction change occasionally
            next_direction = self.generate_random_direction()

        return next_direction

    def update_directon(self, current_time, sound_objects):
        """rotate Animal according to fix angular speed

        Args:
            current_time (float): Time, in seconds, for which the simualtion has been running.
            sound_objects (list): list containing detected sounds
        """
        self.detections_for_directon_change.append(
            self.given_sound_objects_return_detected(
                current_time, sound_objects, detect_self_call=False
            )
        )
        # print(self.id, self.detections_for_directon_change)
        if len(self.detections_for_directon_change)!=0:
            self.direction = self.decide_next_direction(
                self.detections_for_directon_change[-1]
            ).normalize()

        # 600 degrees per second rotation rate at 3 m/s converted to radians
        # self.rotate_towards_given_degree(self.next_direction, 0.010472)

    # def given_next_direction_change_gradually(self, next_dir, decision_time):
    #     current_dir = self.direction
    #     number_of_steps = int(decision_time / self.parameters_df["TIME_STEP"][0])
    #     angle_between_current_and_next_dir = current_dir.angle_between(next_dir)
    #     angle_per
    def deactivate_once_goal_reached(self):
        if self.activation_state:
            # print(self.position, self.destination)
            if self.position.distance_to(self.destination)<2:
                self.activation_state = False
                self.destination = False
            
        if not self.activation_state and not self.destination:
            self.speed = self.parameters_df["Animal_BASE_SPEED"][0]
            self.next_direction = self.direction
            self.detections_for_directon_change = []
        
    def rotate_towards_given_degree(self, new_direction, rotation_rate):
        # want to slowly rotate towards the new_dir from current_dir
        current_direction = self.direction
        if current_direction != new_direction:
            angle_between_current_and_new = current_direction.angle_between(
                new_direction
            )

            if angle_between_current_and_new > rotation_rate:
                rotation_angle = 1 * rotation_rate
            elif angle_between_current_and_new < -rotation_rate:
                rotation_angle = -1 * rotation_rate
            else:
                rotation_angle = angle_between_current_and_new

            rotated_vector = current_direction.rotate(rotation_angle)

            self.direction = rotated_vector.normalize()

    def __repr__(self):
        return f"Animal(id={self.id}, position={self.position})"
