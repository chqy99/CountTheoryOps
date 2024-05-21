import yaml
import os

# base_config 同级目录
script_dir = os.path.dirname(__file__)  # __file__ 是当前脚本的路径
os.chdir(script_dir)

with open('base_config.yaml', 'r', encoding='utf-8') as file:
    base_config = yaml.safe_load(file)

base_tokens = []
reversed = {**base_config["base_reserved"],
            **base_config["dtype"]}
ignore_reversed = base_config["ignore_reserved"]
symbol_rules = {**base_config["symbol"],
                **base_config["binary_operator"],
                **base_config["comp_operator"],
                **base_config["opassign"]}

for str in base_config:
    if str != 'ignore_reserved':
        for key, value in base_config[str].items():
            base_tokens.append(value)
