import LaytonLib.gds
from GUI.utils import to_int


class PuzzleGDSParser:
    def parse_command_name(self, command: LaytonLib.gds.GDSCommand):
        return f"GDSCommand {hex(command.command)}"

    def parse_command_params(self, command: LaytonLib.gds.GDSCommand):
        params = []
        for param in range(len(command.params)):
            params.append(f"param{param}")
        return params

    def parse_type(self, x):
        if isinstance(x, str):
            return "str"
        elif isinstance(x, int):
            return "int"
        elif isinstance(x, float):
            return "float"

    def from_parsed_type(self, s, x):
        if s == "str":
            return str(x)
        elif s == "int":
            return to_int(x)
        elif s == "float":
            return float(x)
        else:
            return str(x)


class InputGDSParser(PuzzleGDSParser):
    def parse_command_name(self, command: LaytonLib.gds.GDSCommand):
        if command.command == 0x43:
            return "Load input background"
        elif command.command == 0x42:
            return "Set answer"
        elif command.command == 0x41:
            return "Set type of input"
        return super().parse_command_name(command)

    def parse_command_params(self, command: LaytonLib.gds.GDSCommand):
        if command.command == 0x43 and len(command.params) == 1:
            return ["Background"]
        elif command.command == 0x42 and len(command.params) == 2:
            return ["Always 0", "Answer"]
        elif command.command == 0x41 and len(command.params) == 4:
            return ["Unk0", "Unk1", "Unk2", "Type of input"]
        return super().parse_command_params(command)


class MultipleChoiceGDSParser(PuzzleGDSParser):
    def parse_command_name(self, command: LaytonLib.gds.GDSCommand):
        if command.command == 0x14:
            return "Create button"
        return super().parse_command_name(command)

    def parse_command_params(self, command: LaytonLib.gds.GDSCommand):
        if command.command == 0x14 and len(command.params) == 5:
            return ["X", "Y", "Button Image", "Is a Solution", "SFX"]
        return super().parse_command_params(command)
