#!/usr/bin/env python3
"""Print the health of every Prometheus scrape target."""
import json, urllib.request

with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/targets") as r:
    targets = json.load(r)["data"]["activeTargets"]

for t in targets:
    print(f'{t["labels"]["job"]:12} {t["health"]:8} {t["lastError"] or "ok"}')
