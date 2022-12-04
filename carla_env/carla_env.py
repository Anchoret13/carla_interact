import glob
import os
import random
import sys
import time

import gym
import pygame
import numpy as np

from gym import spaces

import carla
from carla import agents
from agents.navigation.basic_agent import BasicAgent
from origin_navigation.roaming_agent import RoamingAgent

from carla_env.carla_sync_mode import CarlaSyncMode
from carla_env.carla_weather import Weather

class CarlaEnv(gym.Env):
    def __init__(self, render, carla_port, changing_weather_speed, frame_skip, observations_type, traffic, vehicle_name, map_name, autopilot):
        super(CarlaEnv, self).__init__()

        self.render_display = render
        self.changing_weather_speed = float(changing_weather_speed)
        self.frame_skip = frame_skip
        self.observation_type = observations_type
        self.traffic = traffic
        self.vehicle_name = vehicle_name
        self.map_name = map_name
        self.autopilot = autopilot
        self.actor_list = []
        self.count = 0

        if self.render_display:
            pygame.init()
            self.render_display = pygame.display.set_mode((800, 600), pygame.HWSURFACE | pygame.DOUBLEBUF)
            # self.font = self.get_font()
            self.clock = pygame.time.Clock()

        self.client = carla.Client('localhost', carla_port)
        self.client.set_timeout(4.0)

        self.world.tick()
        actor_list = self.world.get_actors()

        for vehicle in actor_list.filter('*vehicle*'):
            print('REMOVING OLD VEHICLES')
            vehicle.destroy()

        for sensor in actor_list.filter('*sensor*'):
            print('REMOVING OLD SENSORS')
            sensor.destory()

        # create vehicle
        self.vehicle = None
        self.vehicle_list = []
        self._reset_vehicle()
        self.actor_list.append(self.vehicle)

        # initialize blueprint lib
        blueprint_library = self.world.get_blueprint_library()

        # spawn camera for rendering
        if self.render_display:
            self.camera_display = self.world.spawn_actor(
                blueprint_library.find('sensor.camera.rgb'),
                carla.Transform(carla.Location(x = -5.5, z = 2.8), carla.Rotation(pitch = -15)),
                attach_to = self.vehicle
            )
            self.actor_list.append(self.camera_display)

        # spawn camera for pixel observations
        if self.observation_type == 'pixel':
            bp = blueprint_library.find('sensor.camera.rgb')
            bp.set_attribute('image_size_x', str(84))
            bp.set_attribute('image_size_y', str(84))
            bp.set_attribute('fov', str(84))
            location = carla.Location(x=1.6, z=1.7)
            self.camera_vision = self.world.spawn_actor(
                bp, carla.Transform(location, carla.Rotation(yaw=0.0)), attach_to=self.vehicle)
            self.actor_list.append(self.camera_vision)

        # context manager initialization
        if self.render_display and self.observations_type == 'pixel':
            self.sync_mode = CarlaSyncMode(self.world, self.camera_display, self.camera_vision, fps=20)
        elif self.render_display and self.observations_type == 'state':
            self.sync_mode = CarlaSyncMode(self.world, self.camera_display, fps=20)
        elif not self.render_display and self.observations_type == 'pixel':
            self.sync_mode = CarlaSyncMode(self.world, self.camera_vision, fps=20)
        elif not self.render_display and self.observations_type == 'state':
            self.sync_mode = CarlaSyncMode(self.world, fps=20)
        else:
            raise ValueError('Unknown observation_type. Choose between: state, pixel')

        # weather
        self.weather = Weather(self.world, self.changing_weather_speed)

        # collision
        self.collision = False
        sensor_blueprint = self.world.get_blueprint_library().find('sensor.other.collision')
        self.collision_sensor = self.world.spawn_actor(sensor_blueprint, carla.Transform(), attach_to=self.vehicle)
        self.collision_sensor.listen(lambda event: self._on_collision(event))

        self.agent = BasicAgent(self.vehicle)

        # initial observation
        if self.observation_type == 'state':
            obs = self._get_state_obs()
        else:
            obs = np.zeros((3, 84, 84))

        # gym env specific variables
        self.action_space = spaces.Box(-1., 1., shape = (2,), dtype = 'float32')
        self.obs_dim = obs.shape
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=self.obs_dim, dtype='float32')

    def reset(self):
        self._reset_vehicle()
        self.world.tick()
        self._reset_other_vehicles()
        self.world.tick()
        self.count = 0
        self.collision = False
        obs,_,_,_ = self.step([0,0])
        return obs

    def _reset_vehicle(self):
        # choose random spawn point
        init_transforms = self.world.get_map().get_spawn_points()
        vehicle_init_transform = random.choice(init_transforms)

        # create the vehicle
        if self.vehicle is None:
            blueprint_library = self.world.get_blueprint_library()
            vehicle_blueprint = blueprint_library.find('vehicle.' + self.vehicle_name)
            if vehicle_blueprint.has_attribute('color'):
                color = random.choice(vehicle_blueprint.get_attribute('color').recommended_values)
                vehicle_blueprint.set_attribute('color', color)
            self.vehicle = self.world.spawn_actor(vehicle_blueprint, vehicle_init_transform)
        else: 
            self.vehicle.set_transform(vehicle_init_transform)

    def _reset_other_vehicles(self):
        if not self.traffic:
            return

        # clear out old vehicles
        self.client.apply_batch([carla.command.DestroyActor(x) for x in self.vehicles_list])
        self.world.tick()
        self.vehicles_list = []

        # initialize traffic manager
        traffic_manager = self.client.get_trafficmanager()
        traffic_manager.set_global_distance_to_leading_vehicle(2.0)
        traffic_manager.set_synchronous_mode(True)
        traffic_manager.global_percentage_speed_difference(30.0)
        blueprints = self.world.get_blueprint_library().filter('vehicle.*')
        blueprints = [x for x in blueprints if int(x.get_attribute('number_of_wheels')) == 4]

        # choose random spawn points
        num_vehicles = 20
        init_transforms = self.world.get_map().get_spawn_points()
        init_transforms = np.random.choice(init_transforms, num_vehicles)

        # spawn vehicles
        batch = []
        for transform in init_transforms:
            transform.location.z += 0.1  # otherwise can collide with the road it starts on
            blueprint = random.choice(blueprints)
            if blueprint.has_attribute('color'):
                color = random.choice(blueprint.get_attribute('color').recommended_values)
                blueprint.set_attribute('color', color)
            if blueprint.has_attribute('driver_id'):
                driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                blueprint.set_attribute('driver_id', driver_id)
            blueprint.set_attribute('role_name', 'autopilot')
            batch.append(carla.command.SpawnActor(blueprint, transform).then(
                carla.command.SetAutopilot(carla.command.FutureActor, True)))

        for response in self.client.apply_batch_sync(batch, False):
            self.vehicles_list.append(response.actor_id)

        for response in self.client.apply_batch_sync(batch):
            if response.error:
                pass
            else:
                self.vehicles_list.append(response.actor_id)
        
    def _compute_action(self):
        return self.agent.run_step()
    
    def step(self, action):
        rewards = []
        next_obs, done, info = np.array([]), False, {}
        for _ in range(self.frame_skip):
            if self.autopilot:
                vehicle_control = self._compute_action()
                steer = float(vehicle_control.steer)
                if vehicle_control.throttle > 0.0 and vehicle_control.brake == 0.0:
                    throttle_brake = vehicle_control.throttle
                elif vehicle_control.brake >0.0 and vehicle_control.throttle == 0.0:
                    throttle_brake = vehicle_control.brake
                else:
                    throttle_brake = 0.0
                
                action = [throttle_brake, steer]
            next_obs, reward, done, info = self._simulator_step(action)
            rewards.append(reward)

            if done:
                break

        return next_obs, np.mean(rewards), done, info
    
    def should_quit():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCALE:
                    return True
        return False

    def draw_image(surface, image, blend = False):
        array = np.frombuffer(image.raw_data, dtype=np.dtype('uint8'))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        image_surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        if blend:
            image_surface.set_alpha(100)
        surface.blit(image_surface, (0, 0))

    def _simulator_step(self,action):
        if self.render_display:
            if self.should_quit():
                return
            self.clock.tick()

        # calculate actions
        throttle_brake = float(action[0])
        steer = float(action[1])

        if throttle_brake >= 0.0:
            throttle = throttle_brake
            brake = 0.0
        else:
            throttle = 0.0
            brake = -throttle_brake

        vehicle_control = carla.VehicleControl(
            throttle = float(throttle),
            steer = float(steer),
            brake = float(brake),
            hand_brake = False,
            reverse = False,
            manual_gear_shift = False
        )

        self.vehicle.apply_control(vehicle_control)

        if self.render_display and self.observation_type == 'pixel':
            snapshot, display_image, vision_image = self.sync_mode.tick(timeout=2.0)
        elif self.render_display and self.observations_type == 'state':
            snapshot, display_image = self.sync_mode.tick(timeout=2.0)
        elif not self.render_display and self.observations_type == 'pixel':
            snapshot, vision_image = self.sync_mode.tick(timeout=2.0)
        elif not self.render_display and self.observations_type == 'state':
            self.sync_mode.tick(timeout=2.0)
        else:
            raise ValueError('Unknown observation_type. Choose between: state, pixel')

        self.weather.tick()

        # draw the display
        if self.render_display:
            self.draw_image(self.render_display, display_image)
            self.render_display.blit(self.font.render('Frame: %d' % self.count, True, (255, 255, 255)), (8, 10))
            self.render_display.blit(self.font.render('Thottle: %f' % throttle, True, (255, 255, 255)), (8, 28))
            self.render_display.blit(self.font.render('Steer: %f' % steer, True, (255, 255, 255)), (8, 46))
            self.render_display.blit(self.font.render('Brake: %f' % brake, True, (255, 255, 255)), (8, 64))
            self.render_display.blit(self.font.render(str(self.weather), True, (255, 255, 255)), (8, 82))
            pygame.display.flip()

        reward, done, info = self._get_reward()
        if self.observation_type == 'state':
            next_obs = self._get_state_obs()
        else:
            next_obs = self.get_pixel_obs(vision_image)

        self.count += 1

        return next_obs, reward, done, info
    
    def _get_pixel_obs(self, vision_image):
        bgra = np.array(vision_image.raw_data).reshape(84, 84, 4)
        bgr = bgra[:, :, :3]
        rgb = np.flip(bgr, axis=2)
        return rgb
    
    def _get_state_obs(self):
        transform = self.vehicle.get_transform()
        location = transform.location
        rotation = transform.rotation
        x_pos = location.x
        y_pos = location.y
        z_pos = location.z
        pitch = rotation.pitch
        yaw = rotation.yaw
        roll = rotation.roll
        acceleration = vector_to_scalar(self.vehicle.get_acceleration())
        angular_velocity = vector_to_scalar(self.vehicle.get_angular_velocity())
        velocity = vector_to_scalar(self.vehicle.get_velocity())
        return np.array([x_pos,
                         y_pos,
                         z_pos,
                         pitch,
                         yaw,
                         roll,
                         acceleration,
                         angular_velocity,
                         velocity], dtype=np.float64)