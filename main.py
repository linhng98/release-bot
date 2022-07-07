import pygit2
from ruamel import yaml
from typing import Any


def get_value(s: str) -> Any:
    if s.isnumeric():
        return int(s)
    return s


def update_yaml_value(content: dict, path: str, data: str) -> str:
    layers = path.split(".")
    value = content

    for i in range(len(layers)):
        s = get_value(layers[i])

        if i < len(layers) - 1:
            value = value[s]
            continue

        value[s] = data


with open("values.yaml", "r") as fr:
    content = yaml.round_trip_load(fr, preserve_quotes=True)
    update_yaml_value(
        content, "parameters.ai_docker_image.default", "abc.hubhub.asia")

with open("out.yaml", "w") as fw:
    yaml.round_trip_dump(content, stream=fw)
