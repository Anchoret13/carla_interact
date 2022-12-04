from gym.envs.registration import register

register(
    id='simplify-carla-interact-v1',
    entry_point='carla_env.carla_env:CarlaEnv',
    max_episode_steps=500,
    kwargs={
        'render': True,
        'carla_port': 2000,
        'changing_weather_speed': 0.1,
        'frame_skip': 1,
        'observations_type': 'state',
        'traffic': True,
        'vehicle_name': 'tesla.cybertruck',
        'map_name': 'Town05',
        'autopilot': True
    }
)