"""Represents the port class."""


class Port:
    def __init__(self, id: str, name: str, protocol: str, port: str) -> None:
        self.id = id
        self.name = name
        self.protocol = protocol
        self.port = port
        self.size = self.calculate_protocol_port_object_size()
        self.is_risky = False
        self.equal_with = ''

    def __eq__(self, __value: 'Port') -> bool:
        return self.protocol == __value.protocol and self.port == __value.port

    def calculate_protocol_port_object_size(self) -> int:
        size = 1
        if '-' in self.port:
            size = int(self.port.split('-')[1]) - (int(self.port.split('-')[0]) - 1)
        return size

    def _is_risky_port(self, risky_ports: dict) -> bool:
        for protocol, ports in risky_ports.items():
            if ports is not None:
                for port in ports:
                    if self.protocol == protocol and self.port == str(port):
                        return True
        return False

    def get_size(self) -> int:  # noqa: D102
        return int(self.size)