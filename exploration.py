import os
import carla_env
import time
import numpy as np
from stable_baseline3 import SAC
from stable_baseline3.common.moise import NormalActionNoise, OrnsteinUhlenbeckActionNoice
from G29 import *


# ALGORITHM_TYPE = "ppo"
ALGORITHM_TYPE = 'sac'
models_dir = f"models/{ALGORITHM_TYPE}/{int(time.time())}/"
logdir = f"logs/{ALGORITHM_TYPE}/{int(time.time())}/"
if not os.path.exists(models_dir):
	os.makedirs(models_dir)

if not os.path.exists(logdir):
	os.makedirs(logdir)

save_path = '../data_colected'

env = gym.make('simplify-carla-interact-v1')
n_actions = env.action_space.shape[-1]
action_noise = NormalActionNoise(mean = np.zeros(n_actions), sigma = 0.1 * np.ones(n_actions))
human_controller = Controller()

model = SAC("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000, log_interval=4)
model.save("sac_pendulum")
obs = env.reset()
intervene = False

from leaderboard import LeaderboardEvaluator

MAX_ITER = 100
for i in range(MAX_ITER):
	action, _, state = model.predict(obs,deterministic = True)
	obs, reward, done, info = env.step(action)
	env.render()
	if intervene == True:
		os.path.join(save_path, "{i}")
		LeaderboardEvaluator.run()

	if done:
		obs = env.reset()