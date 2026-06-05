---
name: nuc-server-maintenance
description: >
  "Health monitoring & maintenance for NUC/home-server running 24/7 — temperature, load, disk, network checks."
version: 1.0.0
compatibility: Hermes Agent
metadata:
  hermes:
    tags: [sysadmin, linux, nuc, monitoring, maintenance]
    related_skills: [linux-system-relocation, nuc-proxy-setup, verify-system-state]
    trigger: manual
---

# NUC Server Health Monitoring

## Temperature Check (No sudo required)

```bash
# Quick summary: CPU package temp
for f in /sys/class/thermal/thermal_zone*/temp; do
  name=$(cat "$(dirname "$f")/type" 2>/dev/null || echo "unknown")
  temp=$(( $(cat "$f") / 1000 ))
  echo "$name: ${temp}°C"
done
```

**Mapping common thermal zones:**
| Type | What | Typical safe range |
|------|------|--------------------|
| `x86_pkg_temp` | CPU package (core) | 35–85°C |
| `pch_cannonlake` | PCH chipset | 30–70°C |
| `acpitz` | Motherboard / ambient | 25–50°C |

**CPU-specific safe limits:**
- Intel NUC (i5-8259U): Tjunction = **100°C**, throttling starts ~90°C
- Intel N100 / N305: Tjunction = **105°C**
- AMD Ryzen mini PCs: typically 95°C
- **Idle temps**: 35–55°C is normal | **Under load**: up to 85°C is fine

## Load & Resource Check

```bash
echo "Load: $(cat /proc/loadavg)"
echo "---"
free -h
echo "---"
uptime
echo "---"
df -h /
```

**Interpretation:**
- Load average below CPU core count = no bottleneck
- Memory used < 80% = fine
- Disk > 20% free = fine (SSDs: no defrag needed)

## Disk Health (requires sudo or smartmontools)

```bash
sudo apt install -y smartmontools 2>/dev/null
sudo smartctl -H /dev/nvme0n1 2>/dev/null | grep -i "overall\|passed\|failed"
# or for SATA SSD:
# sudo smartctl -H /dev/sda 2>/dev/null | grep -i "overall\|passed\|failed"
```

## 24/7 Server Verdict

| Metric | OK | Warning | Critical |
|--------|:--:|:-------:|:--------:|
| CPU temp (idle) | < 55°C | 55–70°C | > 85°C |
| CPU temp (load) | < 80°C | 80–90°C | > 95°C |
| Load / core ratio | < 1.0 | 1.0–2.0 | > 2.0 |
| Memory used | < 70% | 70–85% | > 90% |
| Uptime | any | — | — |

## Annual Maintenance

- **Dust cleaning**: Every 6–12 months (open NUC case, blow out fan + heatsink)
- **Fan bearing**: NUC fans are ball-bearing, typically last 3–5 years continuous
- **SSD wear**: Check with `sudo smartctl -A /dev/nvme0n1 | grep -i "percentage\|media_error\|critical"` — if `Percentage Used > 10%` per year, normal
- **Thermal paste**: Replace every 3–5 years if temps rise >10°C from baseline

## Pitfalls

- `thermal_zone0` may report -263°C (broken/dummy sensor) — ignore it, look at `x86_pkg_temp`
- `lm-sensors` requires `sudo sensors-detect` then `sudo modprobe coretemp` — the sysfs approach above works without it
- Some NUCs have aggressive fan curves that may not spin up until 60°C+ — brief spikes to 70°C are normal
- If temps are high, check for dust buildup first before assuming hardware failure

## References

Reference files specific to a particular NUC model or scenario live in `references/` within this skill directory.
