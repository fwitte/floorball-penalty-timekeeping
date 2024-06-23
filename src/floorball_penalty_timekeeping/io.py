import json

import pandas as pd


def events_from_json(path, name):
    with open(path, "r") as f:
        data = json.load(f)

    return pd.DataFrame(data[name])
