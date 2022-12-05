import os
import carla_env
import time
import numpy as np
from stable_baseline3 import PPO
from stable_baseline3.common.moise import NormalActionNoise, OrnsteinUhlenbeckActionNoice

ALGORITHM_TYPE = "ppo"
models_dir = f"models/{ALGORITHM_TYPE}/{int(time.time())}/"
logdir = f"logs/{ALGORITHM_TYPE}/{int(time.time())}/"
if not os.path.exists(models_dir):
	os.makedirs(models_dir)

if not os.path.exists(logdir):
	os.makedirs(logdir)
