from typing import Any, Dict, List


def get_value(s: str) -> Any:
    if s.isnumeric():
        return int(s)
    return s


def update_yaml_value(content: dict, path: str, data: str) -> bool:
    layers = path.split(".")
    value = content

    for i in range(len(layers)):
        s = get_value(layers[i])
        if s == None:
            return False

        if i < len(layers) - 1:
            if isinstance(s, str):
                value = value.get(s)
            else:
                value = value[s]

            if value == None:
                return False

            continue

        if value.get(s) == None:
            return False
        value[s] = data

    return True


def append_hyphen(yaml: str) -> str:
    return "---\n" + yaml
