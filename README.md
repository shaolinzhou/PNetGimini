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
- **Logging System** — RotatingFileHandler for automatic log management
- **Network Topology Support** — Cisco Packet Tracer integration for EVE-NG/PNETLab

## Architecture

```
PNetGimini/
├── main.py                     # Entry point: CLI parsing + ThreadPool dispatch
├── src/
│   ├── models/
│   │   ├── device.py           # Device model: IP, port, credentials, commands
│   │   └── command.py          # Command model: category (config/show) + commands
│   ├── core/
│   │   ├── config_parser.py    # YAML parser → Device/Command objects
│   │   ├── device_manager.py   # SSH/Telnet connection + execute + backup + rollback
│   │   └── result_handler.py   # JSON/TXT report generation
│   └── utils/
│       └── logger.py           # RotatingFileHandler logging
├── configs/                    # Device configurations
│   ├── devices.yaml            # Main device configuration file
│   └── devices_enetlab.pkt     # Cisco Packet Tracer topology for EVE-NG
├── logs/                       # System runtime logs (auto-generated)
├── outputs/                    # Deployment reports and snapshots
│   ├── deployment_report_*.txt # Human-readable deployment reports
│   └── summary_report_*.json   # Machine-readable summary reports
├── config_to_yaml.py           # Reverse tool: .conf → YAML recovery script
└── requirements.txt            # Python dependencies
```

## Installation

### Prerequisites

- Python 3.8+
- EVE-NG/PNETLab or physical Cisco/Huawei devices
- Cisco Packet Tracer (for topology import)

### Setup

```bash
# Clone the repository
git clone https://github.com/shaolinzhou/PNetGimini.git
cd PNetGimini

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Import Network Topology

1. **Import into EVE-NG**:
   - Open EVE-NG web interface
   - Create a new lab
   - Import the `configs/devices_enetlab.pkt` topology
   - Start all devices

2. **Verify Topology**:
   - Ensure all devices are running
   - Note the management IP addresses and console ports

### 2. Configure Devices

Edit `configs/devices.yaml` with your device configurations:

```yaml
devices:
  - ip: 10.48.80.40          # EVE-NG management IP
    port: 30001               # Console port
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

### 3. Deploy Configurations

```bash
# Default config: configs/devices.yaml
python main.py

# Specify custom config file
python main.py configs/custom_config.yaml
```

### 4. Reverse Engineering (Recovery)

```bash
# Convert .conf backups to recovery YAML
python config_to_yaml.py
```

## Network Topology

### Topology File: `configs/devices_enetlab.pkt`

- **Purpose**: Defines the network topology for EVE-NG/PNETLab simulation
- **Format**: Cisco Packet Tracer (.pkt) file
- **Usage**: Import into EVE-NG to build the physical network topology that PNetGimini will configure

### Topology Components

The topology typically includes:
- **Cisco Routers** (e.g., R0, R1, R2, R3, R4)
- **Cisco Switches** (e.g., SW0, SW1, SW2, SW3, SW4, M-SW0, M-SW1, M-SW2)
- **VLAN configurations** (VLAN 10, 20, 30, 40, 50)
- **Routing protocols** (RIP, OSPF)
- **NAT/PAT configurations**
- **DHCP pools**

### Mapping Topology to devices.yaml

```yaml
# Example mapping from topology to devices.yaml
devices:
  - ip: 10.48.80.40      # EVE-NG management IP
    port: 30001           # Console port for Router R0
    username: admin
    password: admin
    device_type: cisco_ios_telnet
    commands:
      config:
        - hostname R0
        # ... configuration commands
```

## Output Structure

### Logs Directory (`logs/`)

```
logs/
└── automation.log           # System runtime logs (auto-rotated, max 10MB × 5 files)
```

### Outputs Directory (`outputs/`)

```
outputs/
├── deployment_report_{timestamp}.txt     # Human-readable deployment report
└── summary_report_{timestamp}.json       # Machine-readable summary report
```

### Report Contents

**Deployment Report (TXT)**:
- Device connection status
- Command execution results
- Error messages and rollback actions
- Timestamp and duration

**Summary Report (JSON)**:
- Total devices processed
- Success/error counts
- Individual device status
- Execution metadata

## Configuration

### Device Configuration (devices.yaml)

```yaml
devices:
  - ip: <management_ip>
    port: <console_port>
    username: <username>
    password: <password>
    device_type: cisco_ios_telnet  # or cisco_ios_ssh, huawei_telnet, etc.
    commands:
      config:
        - <configuration_command_1>
        - <configuration_command_2>
      show:
        - <show_command_1>
        - <show_command_2>
```

### Supported Device Types

| Device Type | Protocol | Platform |
|-------------|----------|----------|
| `cisco_ios_telnet` | Telnet | Cisco IOS |
| `cisco_ios_ssh` | SSH | Cisco IOS |
| `huawei_telnet` | Telnet | Huawei VRP |
| `huawei_ssh` | SSH | Huawei VRP |

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

### Current Features (v1.x)

- ✅ YAML-based configuration
- ✅ Multi-threaded deployment
- ✅ Automatic backup and rollback
- ✅ Dual-format reports
- ✅ Real-time terminal output
- ✅ Network topology support

### Future Vision: Sentinel CPNA

- **Async I/O Engine** — Migrate from ThreadPool to pure asyncio
- **gNMI/NETCONF Support** — Replace CLI with model-driven protocols
- **Physics-Aware Engine** — ODE-based temperature/load → network delay prediction
- **Dynamic Concurrency** — Adjust parallel connections based on device health score
- **CMDB Integration** — NetBox/ServiceNow for asset lifecycle context
- **MQTT Sensor Integration** — External environmental monitoring

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by CAE (Computer-Aided Engineering) methodology
- Built with Netmiko for network device communication
- Designed for EVE-NG/PNETLab simulation environments
