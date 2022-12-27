import matplotlib.pyplot as plt
import numpy as np
import torch
import os
import json
import gym
import argparse

from environments.parallel_envs import make_vec_envs, make_env
from utils import helpers as utl

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def test_policy(load_path, iter):
    with open(os.path.join(load_path, "config.json"),'r', encoding='UTF-8') as f:
        data_dict = json.load(f)
    args = argparse.ArgumentParser()
    for key, val in data_dict.items():
        args.add_argument("-" + key, default=val)
        
    args = args.parse_args()
    

    env_name = args.env_name
    
    if hasattr(args, 'test_env_name'):
        env_name = args.test_env_name

    test_env = gym.make(env_name)
    num_steps = 50
    policy = torch.load(os.path.join(load_path, 'models/policy{}.pt'.format(iter)))
    encoder = torch.load(os.path.join(load_path, 'models/encoder{}.pt'.format(iter)))

    # reset environment
    state = test_env.reset()
    state = torch.from_numpy(state).float().to(device).unsqueeze(0)
    # state = np.concatenate([state, [0.0]], axis=0)

    if encoder is not None:
        # reset latent state to prior
        latent_sample, latent_mean, latent_logvar, hidden_state = encoder.prior(1)
    else:
        latent_sample = latent_mean = latent_logvar = hidden_state = None

    ret = 0
    devi_p = 0
    devi_v = 0
    devi_phi = 0
    punish_steer = 0
    punish_a_x = 0
    punish_yaw_rate = 0
    
    for step_idx in range(num_steps):

        with torch.no_grad():
            _, action = utl.select_action(args=args,
                                            policy=policy,
                                            state=state,
                                            belief=None,
                                            task=None,
                                            latent_sample=latent_sample,
                                            latent_mean=latent_mean,
                                            latent_logvar=latent_logvar,
                                            deterministic=True)

        # observe reward and next obs
        state, rew_raw, done, info = test_env.step(action.cpu().numpy()[0])
        ret += rew_raw
        devi_p += info['scaled_devi_p']
        devi_v += info['scaled_devi_v']
        devi_phi += info['scaled_devi_phi']
        punish_steer += info['scaled_punish_steer']
        punish_a_x += info['scaled_punish_a_x']
        punish_yaw_rate += info['scaled_punish_yaw_rate']
        
        state = torch.from_numpy(state).float().to(device).unsqueeze(0)
        rew_raw = torch.from_numpy(np.array([rew_raw])).float().to(device)
        # done = torch.from_numpy(done).float().to(device)
        # state = np.concatenate([state, 0.0])
        # test_env.render()

        if encoder is not None:
            # update the hidden state
            latent_sample, latent_mean, latent_logvar, hidden_state = utl.update_encoding(encoder=encoder,
                                                                                            next_obs=state,
                                                                                            action=action,
                                                                                            reward=rew_raw,
                                                                                            done=None,
                                                                                            hidden_state=hidden_state)
        latent_sample, latent_mean, latent_logvar, hidden_state = latent_sample.unsqueeze(0), latent_mean.unsqueeze(0), latent_logvar.unsqueeze(0), hidden_state.unsqueeze(0)

        if done:
            break
    print("return: ", ret, 
          "devi_p: ", devi_p,
          "devi_v: ", devi_v,
          "devi_phi: ", devi_phi,
          "punish_punish_steer: ", punish_steer,
          "scaled_punish_a_x: ", punish_a_x,
          "punish_punish_yaw_rate: ", punish_yaw_rate)
    print('-'*100)
        

def main():
    load_path = "./logs/logs_MultiGoalEnv-v0/varibad_74__28:12_00:06:57"
    iter = 499
    for i in range(10):
        test_policy(load_path, iter)


if __name__ == "__main__":
    main()