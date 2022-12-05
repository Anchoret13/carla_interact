import gym
import carla_env

# if __name__ == '__main__':
#     env = gym.make('simplify-carla-interact-v1')
#     env.reset()
#     done = False
#     while not done:
#         next_obs, reward, done, info = env.step([-0.5, 0.3])

import numpy as np
from stable_baselines3 import DDPG,PPO
from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

env = gym.make('simplify-carla-interact-v1')
n_actions = env.action_space.shape[-1]
action_noise = NormalActionNoise(mean = np.zeros(n_actions), sigma = 0.1 * np.ones(n_actions))

model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=50, log_interval=10)
model.save("PPO_drive")
env = model.get_env()
del model
# model = PPO.load("PPO_drive")
# obs = env.reset()
# while True:
#     action, _states = model.predict(obs)
#     obs, rewards, dones, info = env.step(action)
#     env.render()