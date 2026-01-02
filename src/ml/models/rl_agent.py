from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import gymnasium as gym
import numpy as np

class RLAgent:
    def __init__(self, env: gym.Env, verbose: int = 1):
        self.env = DummyVecEnv([lambda: env])
        self.model = PPO(
            "MlpPolicy", 
            self.env, 
            verbose=verbose,
            tensorboard_log="./tensorboard_logs/"
        )
        
    def train(self, total_timesteps: int = 10000):
        self.model.learn(total_timesteps=total_timesteps)
        
    def predict(self, observation):
        action, _ = self.model.predict(observation, deterministic=True)
        return action
        
    def save(self, path: str):
        self.model.save(path)
        
    def load(self, path: str):
        self.model = PPO.load(path, env=self.env)
