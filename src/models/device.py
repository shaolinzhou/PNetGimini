from typing import Optional, List

class Device:
    """
    Device data model representing a target network device.
    """
    def __init__(self, ip: str, port: int, username: str, password: str, device_type: str, secret: Optional[str] = None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.device_type = device_type
        self.secret = secret if secret is not None else password
        self.commands: List = []

    def add_command(self, command_obj):
        """Add a command object to the device."""
        self.commands.append(command_obj)

    def __str__(self):
        return f"{self.ip}:{self.port}:{self.username}:***:{self.device_type}"