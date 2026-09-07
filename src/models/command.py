class Command:
    """
    命令数据模型，包含命令类别和命令列表。
    """
    def __init__(self, category: str, commands: list):
        self.category = category
        self.commands = commands