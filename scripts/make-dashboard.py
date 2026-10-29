#!/usr/bin/env python3
"""Generate the Grafana dashboard JSON for the Ethereum node SRE lab."""
import json, pathlib

def ts(id_, title, targets, x, y, w=12, h=8, unit="none", stack=False, thresholds=None):
    custom = {"fillOpacity": 60 if stack else 10, "lineWidth": 2, "showPoints": "never"}
    if stack:
        custom["stacking"] = {"mode": "normal", "group": "A"}
    defaults = {"unit": unit, "custom": custom}
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
        custom["thresholdsStyle"] = {"mode": "line"}
    return {"id": id_, "type": "timeseries", "title": title,
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "targets": targets, "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "multi"}}}

def q(expr, legend="", ref="A", instant=False, fmt="time_series"):
    return {"refId": ref, "expr": expr, "legendFormat": legend,
            "instant": instant, "range": not instant, "format": fmt}

LAG = "slotclock_present_slot - beacon_head_state_slot"
LAG_STEPS = [{"color": "green", "value": None},
             {"color": "orange", "value": 8},
             {"color": "red", "value": 32}]

panels = [
    # Row 1: at-a-glance health
    {"id": 1, "type": "stat", "title": "Consensus head lag (slots)",
     "gridPos": {"x": 0, "y": 0, "w": 6, "h": 6},
     "targets": [q(LAG, "lag")],
     "fieldConfig": {"defaults": {"unit": "none", "decimals": 0,
                                  "thresholds": {"mode": "absolute", "steps": LAG_STEPS}},
                     "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "background",
                 "graphMode": "area", "textMode": "value"}},
    {"id": 9, "type": "stat", "title": "Scrape availability (last 1h)",
     "gridPos": {"x": 6, "y": 0, "w": 9, "h": 6},
     "targets": [q("avg_over_time(up[1h]) * 100", "{{job}}")],
     "fieldConfig": {"defaults": {"unit": "percent", "decimals": 2,
                                  "thresholds": {"mode": "absolute", "steps": [
                                      {"color": "red", "value": None},
                                      {"color": "orange", "value": 99},
                                      {"color": "green", "value": 99.9}]}},
                     "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value",
                 "graphMode": "none", "textMode": "value_and_name"}},
    {"id": 10, "type": "table", "title": "Active alerts",
     "gridPos": {"x": 15, "y": 0, "w": 9, "h": 6},
     "targets": [q('ALERTS{alertstate="firing"}', "", instant=True, fmt="table")],
     "fieldConfig": {"defaults": {"noValue": "All clear"}, "overrides": []},
     "transformations": [{"id": "organize", "options": {"excludeByName": {
         "Time": True, "Value": True, "__name__": True, "alertstate": True}}}],
     "options": {"showHeader": True}},
    # Row 2: consensus health and peers
    ts(2, "Consensus head lag over time (slots)", [q(LAG, "lag")], 0, 6,
       thresholds=LAG_STEPS),
    ts(3, "Peers", [q("libp2p_peers", "Lighthouse", "A"), q("p2p_peers", "Geth", "B")], 12, 6),
    # Row 3: execution progress and the CPU incident
    ts(4, "Geth chain progress", [q("chain_head_header", "Header", "A"),
                                  q("chain_head_block", "Block", "B")], 0, 14),
    ts(5, "CPU by mode (cores in use)",
       [q('sum by (mode) (rate(node_cpu_seconds_total{mode!="idle"}[2m]))', "{{mode}}")],
       12, 14, stack=True),
    # Row 4: host resources
    ts(6, "Load vs CPU count", [q("node_load1", "Load (1m)", "A"),
                                q('count(node_cpu_seconds_total{mode="idle"})', "CPU count", "B")],
       0, 22, w=8),
    ts(7, "Memory available", [q("node_memory_MemAvailable_bytes", "available")],
       8, 22, w=8, unit="bytes"),
    ts(8, "Disk available on /", [q('node_filesystem_avail_bytes{mountpoint="/"}', "available")],
       16, 22, w=8, unit="bytes"),
]

dashboard = {
    "uid": "eth-node-sre", "title": "Ethereum Node SRE (Hoodi)",
    "tags": ["ethereum", "hoodi", "sre"], "timezone": "browser",
    "schemaVersion": 39, "version": 1, "editable": True, "refresh": "30s",
    "time": {"from": "now-3h", "to": "now"}, "panels": panels,
}

out = pathlib.Path(__file__).resolve().parent.parent / "grafana/provisioning/dashboards/ethereum-node-sre.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(dashboard, indent=2))
print(f"Wrote {out} with {len(panels)} panels")
