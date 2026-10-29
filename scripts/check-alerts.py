#!/usr/bin/env python3
"""List every alert rule and its current state."""
import json, urllib.request

with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/rules") as r:
    groups = json.load(r)["data"]["groups"]

for g in groups:
    for rule in g["rules"]:
        print(f'{rule["name"]:26} {rule["state"]}')
