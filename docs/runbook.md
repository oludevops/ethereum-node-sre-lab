# Runbook

Quick reference for the alerts and routine tasks. Commands assume you're in `~/ethereum-node-sre-lab`.

## First checks for any alert

```bash
scripts/check-alerts.py
scripts/check-targets.py
systemctl status geth lighthouse --no-pager | grep -E 'Active|Main PID'
uptime
```

## ScrapeTargetDown

A metrics endpoint isn't answering.

- Check the service is running: `systemctl status <geth|lighthouse>`
- Check the endpoint directly: `curl -s 127.0.0.1:6060/debug/metrics/prometheus | head` (Geth), `curl -s 127.0.0.1:5054/metrics | head` (Lighthouse), `curl -s 127.0.0.1:9100/metrics | head` (node_exporter)
- If the service is up but scrapes fail, it's usually too slow to respond. Check load and the slowest scrape:

```bash
curl -s --data-urlencode 'query=max_over_time(scrape_duration_seconds[1h])' 127.0.0.1:9090/api/v1/query
```

Lighthouse takes around 7-8 minutes after a restart before its metrics come back. Don't restart it again during that time.

## ConsensusHeadLagging / ConsensusHeadLagCritical

Lighthouse is behind the network clock.

```bash
journalctl -u lighthouse -n 20 --no-pager
journalctl -u geth -n 20 --no-pager | grep -iE 'error|warn'
```

- Low peers in the Lighthouse "Syncing" lines: it's a network problem.
- Engine API timeouts (`127.0.0.1:8551 ... timed out`): Geth is too busy. Check CPU with `top -b -n1 -o %CPU | head -15`.
- If kcompactd is near the top, check the settings in `host-tuning/` are applied:

```bash
sysctl vm.compaction_proactiveness
cat /sys/kernel/mm/transparent_hugepage/defrag
```

During Geth's initial sync some lag is expected on this VM.

## ExecutionHeadStalled

Geth's head hasn't moved in 5 minutes (only active after initial sync).

- Is Lighthouse running? Geth can't advance without it.
- Check Geth's logs for errors and peers: `journalctl -u geth -n 30 --no-pager`

## LowConsensusPeers / LowExecutionPeers

- Check outbound internet access from the VM.
- Peer counts drop after restarts and recover over a few minutes.
- The node is outbound-only behind NAT, so counts run lower than a node with open P2P ports.

## HostCpuSaturated

```bash
top -b -n1 -o %CPU | head -15
```

Look for anything that isn't Geth, Lighthouse or the monitoring stack and stop it. If it's just the two clients, the VM needs more vCPUs.

## DiskSpaceLow / DiskWillFillIn24h

```bash
df -h /
sudo du -sh /var/lib/geth /var/lib/lighthouse
docker system df
```

Clean up Docker images and old files first. If the chain data itself is the problem, the VM needs a bigger disk.

## Routine tasks

**Stop the node cleanly** (Geth needs time to flush to disk; the unit allows 10 minutes):

```bash
sudo systemctl stop lighthouse geth
```

**Start it:**

```bash
sudo systemctl start geth lighthouse
```

**Reload Prometheus after editing config or alerts:**

```bash
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker compose exec prometheus promtool check rules /etc/prometheus/alerts.yml
curl -s -X POST 127.0.0.1:9090/-/reload
```

**Rebuild the dashboard after editing the script:**

```bash
scripts/make-dashboard.py
```

Grafana picks it up within 30 seconds.

**Rotate the Grafana admin password:**

```bash
NEWPW=$(openssl rand -base64 18)
docker compose exec grafana grafana cli admin reset-admin-password "$NEWPW"
sed -i "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$NEWPW|" .env
unset NEWPW
```
