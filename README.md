Interactive Carla env based on [THIS](https://github.com/janwithb/carla-gym-wrapper)
<!-- --carla-server -->

# Multi Intention IRL in CARLA

To run this code, you need to first install CARLA 0.9.13, and run the carla with

```
bash CarlaUE4.sh --carla-server
```

Then go to data_collect folder to collect data

```
# ===> pls remeber to change this one
export CODE_FOLDER=/home/dyf/workspace/carla-expert
export CARLA_ROOT=/home/dyf/CARLA_0.9.13.1
# ===> pls remeber to change this one
export SCENARIO_RUNNER_ROOT=${CODE_FOLDER}/scenario_runner
export LEADERBOARD_ROOT=${CODE_FOLDER}/leaderboard
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":"${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg":"${CODE_FOLDER}/team_code":${PYTHONPATH}
```

After start running CARLA, run 
```
python team_code/run_collect.py carla_sh_path=${CARLA_ROOT}/CarlaUE4.sh absolute_path=${CODE_FOLDER}
```

To run RL process, simply run
```
python exploration.py
```

If you want to intervene, currently I implement intervention with steering wheel, because I can't do good with keyboard, which may lead to bad intervention and poor performance.

## ABOUT MULTI-INTENTION IRL
There are still many issues that stop me from running multi-intention IRL, f-irl and max-ent in f-irl folder is available.