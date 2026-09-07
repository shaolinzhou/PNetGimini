# PNetGimini Configuration & Snapshot Guide (`configs/`)

This directory contains target device inventories, deployment templates, pre-change configuration snapshots, and topology reference files.

---

## 📁 Directory Structure

```
configs/
├── README.md               # Configuration guide (this file)
├── devices.yaml            # Primary deployment inventory & instruction file
├── devices_enetlab.pkt     # Cisco Packet Tracer simulation topology
├── latest_recovery.yaml    # Auto-generated YAML recovery template (from config_to_yaml.py)
└── snapshots/              # Automated pre-change running-config backups (.conf)
```

---

## 📝 1. `devices.yaml` Specification

`devices.yaml` is the primary inventory and intent definition file.

### Complete Schema:
```yaml
devices:
  - ip: "10.48.80.40"                    # Device management IP or Lab Host IP
    port: 30001                          # Port (e.g. 22 for SSH, 23 or 30000+ for lab Telnet)
    username: "admin"
    password: "admin"
    device_type: "cisco_ios_telnet"      # cisco_ios_telnet, cisco_ios_ssh, huawei_router_telnet, huawei_router_ssh
    commands:
      # 1. Configuration block (automatically uses send_config_set with diff rollback tracking)
      config:
        - hostname R0
        - interface Ethernet0/0
        - ip address 192.168.1.1 255.255.255.0
        - no shutdown
        - router ospf 1
        - network 192.168.1.0 0.0.0.255 area 0

      # 2. Verification / Show commands (read-only output captured into audit reports)
      show:
        - show ip interface brief
        - show ip route
        - ping 192.168.1.254

      # 3. Proactive Assertion block (fails trigger automatic diff rollback)
      verify:
        - ping 192.168.1.254
```

### Supported Device Types:
| `device_type` in YAML | Protocol | Vendor Platform |
|---|---|---|
| `cisco_ios_telnet` | Telnet | Cisco IOS / IOS-XE |
| `cisco_ios_ssh` | SSH | Cisco IOS / IOS-XE |
| `huawei_router_telnet` | Telnet | Huawei VRP |
| `huawei_router_ssh` | SSH | Huawei VRP |

---

## 📸 2. Pre-Change Snapshots (`snapshots/`)

Before applying any modification to a target device, `DeviceManager` automatically captures its complete running configuration:

- **Naming Convention**: `{ip}_{port}_snapshot_{timestamp}.conf`
- **Location**: `configs/snapshots/` (or `[output_dir]/snapshots/`)
- **Use Cases**:
  1. Automated fallback source for `ConfigDiffEngine` rollback.
  2. Audit trails of device state prior to changes.
  3. Input source for the reverse engineering tool (`config_to_yaml.py`).

---

## 🔄 3. Disaster Recovery Workflow (`config_to_yaml.py`)

If you need to restore all lab devices to their latest known snapshot state:

1. Run the reverse engineering utility:
   ```bash
   python config_to_yaml.py
   ```
2. The tool scans `configs/snapshots/`, automatically determines the most recent `.conf` file for each unique `(IP, Port)`, cleans out noise headers, and generates:
   ```
   configs/latest_recovery.yaml
   ```
3. Deploy the recovery configuration:
   ```bash
   python main.py configs/latest_recovery.yaml
   ```

---

## 🌐 4. Lab Topology: `devices_enetlab.pkt`

- Open this file in **Cisco Packet Tracer** to inspect the reference topology, IP addressing plan, and interface mappings.
- For EVE-NG / PNETLab users, map the router ports (30001~30021) in `devices.yaml` to your corresponding virtual node telnet console ports.
