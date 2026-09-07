# PNetGimini

**Provisioning Network Gemini System** — A physics-aware network automation deployment system.

## Overview

PNetGimini is a network automation tool that borrows from CAE (Computer-Aided Engineering) methodology for segmenting complex simulation tasks. It deploys configurations to multi-vendor network devices (Cisco/Huawei) via SSH/Telnet, with automatic backup, rollback, and structured reporting.

Inspired by finite element analysis (FEA) domain decomposition methods, the system treats network configuration as a multi-physics problem — separating basic data (IP/VLAN), routing convergence (OSPF/BGP), and post-processing (security/QoS) into distinct execution blocks with appropriate timing.

## Features

- **YAML-based Configuration** — Structured device inventory and command definitions
- **Multi-threaded Deployment** — ThreadPoolExecutor for parallel device provisioning
- **Automatic Pre-change Backup** — Snapshots running-config before any modification
- **Rollback Mechanism** — Auto-restore on connection failure or execution error
- **Dual-format Reports** — JSON (machine-readable) + TXT (human-readable)
- **Reverse Engineering Tool** — Extract commands from .conf backups to generate recovery YAML
- **Project-level Isolation** — Configs, logs, outputs scoped to project directory
- **Real-time Terminal Output** — Live command execution feedback

## Architecture

```
main.py                     # Entry point: CLI parsing + ThreadPool dispatch
├── src/models/
│   ├── device.py           # Device model: IP, port, credentials, commands
│   └── command.py          # Command model: category (config/show) + commands
├── src/core/
│   ├── config_parser.py    # YAML parser → Device/Command objects
│   ├── device_manager.py   # SSH/Telnet connection + execute + backup + rollback
│   └── result_handler.py   # JSON/TXT report generation
├── src/utils/
│   └── logger.py           # RotatingFileHandler logging
├── config_to_yaml.py       # Reverse tool: .conf → YAML recovery script
└── configs/                # Device configs + snapshots + reports (project-isolated)
```

## Installation

### Prerequisites

- Python 3.8+
- PNETLab or physical Cisco/Huawei devices

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd PnetGimini

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Run

```bash
# Default config: configs/devices.yaml
python main.py

# Specify custom config
python main.py configs/project1.yaml
```

### Configuration Format (devices.yaml)

```yaml
devices:
  - ip: 192.168.1.1
    port: 30001
    username: admin
    password: admin
    device_type: cisco_ios_telnet
    commands:
      config:
        - hostname R1
        - interface e0/0
        - ip address 192.168.1.1 255.255.255.0
        - no shutdown
      show:
        - show ip interface brief
        - show ip route
```

### Reverse Engineering (Recovery)

```bash
# Convert .conf backups to recovery YAML
python config_to_yaml.py
```

## Output Structure

```
configs/
├── devices.yaml                          # Input configuration
├── {ip}_{port}_snapshot_{timestamp}.conf # Pre-change backup
├── summary_report_{timestamp}.json       # Machine-readable report
└── deployment_report_{timestamp}.txt     # Human-readable report
```

## Version History

| Version | Changes |
|---------|---------|
| v1.0 | Initial implementation with custom # markup parsing |
| v1.1 | Fixed configuration file parsing failure |
| v1.2 | Migrated to YAML configuration format |
| v1.3 | Fixed file path resolution error |
| v1.4 | Added special handling for ping command timeout |
| v1.5 | Added real-time terminal output |
| v1.6 | Fixed report output file overwrite bug |

## Roadmap

### Sentinel CPNA (Future Vision)

- **Async I/O Engine** — Migrate from ThreadPool to pure asyncio
- **gNMI/NETCONF Support** — Replace CLI with model-driven protocols
- **Physics-Aware Engine** — ODE-based temperature/load → network delay prediction
- **Dynamic Concurrency** — Adjust parallel connections based on device health score
- **CMDB Integration** — NetBox/ServiceNow for asset lifecycle context
- **MQTT Sensor Integration** — External environmental monitoring

## License

MIT License
