from typing import Optional, List

class Device:
    """
    Device data model representing a target network device.
    Supports SSH password, Telnet passwordless, SSH private key authentication, and enable secret.
    """
    def __init__(
        self,
        ip: str,
        port: int,
        username: str = "",
        password: str = "",
        device_type: str = "",
        secret: Optional[str] = None,
        key_file: Optional[str] = None,
        passphrase: Optional[str] = None,
        name: Optional[str] = None,
        node_id: Optional[str] = None
    ):
        self.ip = ip
        self.port = port
        self.username = username or ""
        self.password = password or ""
        self.device_type = device_type
        self.secret = secret if secret is not None else self.password
        self.key_file = key_file
        self.passphrase = passphrase
        self.name = name
        self.node_id = node_id
        self.commands: List = []

    def add_command(self, command_obj):
        """Add a command object to the device."""
        self.commands.append(command_obj)

    def __str__(self):
        auth_mode = "key" if self.key_file else "pwd"
        label = f"[{self.name}] " if self.name else ""
        return f"{label}{self.ip}:{self.port}:{self.username}:***({auth_mode}):{self.device_type}"