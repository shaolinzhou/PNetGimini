class Device:
    """
    设备数据模型。
    """
    def __init__(self, ip: str, port: int, username: str, password: str, device_type: str):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.device_type = device_type
        self.commands = []

    def add_command(self, command_obj):
        """添加一个命令对象到设备。"""
        self.commands.append(command_obj)

    def __str__(self):
        return f"{self.ip}:{self.port}:{self.username}:***:{self.device_type}"