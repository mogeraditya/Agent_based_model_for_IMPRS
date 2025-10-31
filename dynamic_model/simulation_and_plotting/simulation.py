"""Contains the code that describes a Simulation object. Runs one instance, given parameters."""

import os
import pickle
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.append("./dynamic_model")
from agents.animals import Animal
from agents.sounds import Sound
from supporting_files.utilities import creation_time_calculation, load_parameters
from supporting_files.vectors import Vector


class Simulation:
    """one instance of the simulation;
    this object's goal is to run the simulation for one
    instance of the set of parameters chosen
    """

    def __init__(self, parameters_df, output_dir):
        # parameters_df = load_parameters(parameter_file_dir)
        Animal._id_counter = 0

        self.parameters_df = parameters_df
        self.output_dir = output_dir
        self.dir_to_store = self.output_dir + "/data_for_plotting/"

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.dir_to_store, exist_ok=True)

        self.animals = [
            Animal(self.parameters_df, self.output_dir)
            for _ in range(int(self.parameters_df["NUM_Animals"][0]))
        ]

        self.sound_objects = []  # Contains both Sound
        self.time_elapsed = 0.0
        self.history = []

        self.handles = []

        with open(self.dir_to_store + "animals_initial.pkl", "wb") as f:
            pickle.dump(self.animals, f)
 

    def run(self):
        """Runs one instance of the simulation.
        After parsing the parameter file, it runs one instance of the simulation
        for those sets of parameters.
        """
        num_steps = int(
            self.parameters_df["SIM_DURATION"][0] / self.parameters_df["TIME_STEP"][0]
        )
        start_timing = datetime.now()
        list_time_taken_for_each_loop = []
        save_time_of_last_iter = start_timing
        for step in range(num_steps):
            self.time_elapsed = step * self.parameters_df["TIME_STEP"][0]

            for sound in self.sound_objects:
                # print(self.sound_objects)
                sound.update(self.time_elapsed)
                if sound.current_spl < self.parameters_df["MIN_DETECTABLE_SPL"][0]:
                    sound.active = False

            for animal in self.animals:
                animal.update(self.time_elapsed, self.sound_objects)


            self.history.append(
                {
                    "time": self.time_elapsed,
                    "animal_positions": [
                        (animal.position.x, animal.position.y) for animal in self.animals
                    ],
                    "animal_directions": [
                        (animal.direction.normalize().x, animal.direction.normalize().y)
                        for animal in self.animals
                    ],
                    "animal_detections": [
                        animal.get_detections_at_time(self.time_elapsed)
                        for animal in self.animals
                    ],
                    "sound_objects": [
                        self.serialize_sound(s)
                        for s in self.sound_objects
                        if s.active
                    ],
                    "sound_objects_count": len(self.sound_objects),
                    "next_dir_angle": [
                        animal.next_direction.angle_between(Vector(1, 0))
                        for animal in self.animals
                    ],
                    "current_dir_angle": [
                        animal.direction.angle_between(Vector(1, 0)) for animal in self.animals
                    ],
                }
            )

            self.sound_objects = [
                s for s in self.sound_objects if s.active
            ]

            current_loop_time = datetime.now()
            list_time_taken_for_each_loop.append(
                current_loop_time - save_time_of_last_iter
            )
            # print(current_loop_time-save_time_of_last_iter)
            save_time_of_last_iter = current_loop_time
            self.handle_data_storage_for_plotting(self.time_elapsed, False)
        self.handle_data_storage_for_plotting(self.time_elapsed, True)
        print(f"total_time_taken_to_store_info: {save_time_of_last_iter-start_timing}")
        print(f"average_time_per_loop {np.mean(list_time_taken_for_each_loop)}")
        # self.save_simulation_data()
        print("DATA SAVED")

    def handle_data_storage_for_plotting(self, current_time, is_end_of_code):
        """Generates files for data used for plotting.
        Periodically the history list is cleared to ensure
        RAM doesnt get used up.
        """
        history_array_size_limit = self.parameters_df["CLEANUP_PLOT_DATA"][0]

        # filepath = os.path.join(self.output_dir, _dir_to_save)
        if len(self.history) > history_array_size_limit or is_end_of_code:
            with open(
                self.dir_to_store + f"history_dump_{current_time:.3f}.pkl", "wb"
            ) as f:
                pickle.dump(self.history, f)
            self.history = []

        if is_end_of_code:

            self.parameters_df.to_pickle(self.dir_to_store + "/parameters_used.pkl")
        #     print(f"Saved simulation data to {filepath}")


    def serialize_sound(self, sound):
        """Serializes sounds into dictionaries.
        This is done for easier storage.

        Args:
            sound (EchoSound): input sound object to be serialized

        Returns:
            dict: data inside the sound obejct is serialized into a dict.
        """
        data = {
            "origin": (sound.origin.x, sound.origin.y),
            "radius": sound.current_radius,
            "spl": sound.current_spl,
            "emitter_id": sound.emitter_id,
            "status": sound.active,
        }
        # print(data["type"])
        return data


if __name__ == "__main__":
    OUTPUT_DIR = r"./simulation_runs2/"
    PARAMETER_FILE_DIR = r"./dynamic_model/paramsets/common_parameters.csv"
    PARAMETER_DF = load_parameters(PARAMETER_FILE_DIR)
    sim = Simulation(PARAMETER_DF, OUTPUT_DIR)
    sim.run()
