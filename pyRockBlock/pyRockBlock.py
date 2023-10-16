from datetime import datetime, timedelta
from serial import Serial, SerialException
import logging


class RockBlockException(Exception):
    pass


class RockBlock:

    IRIDIUM_EPOCH = datetime.fromisoformat("2014-05-11T14:23:55")

    def __init__(self, port, timeout=5):
        self.port = port
        self.s = None
        self.timeout = timeout
        self.logger = logging.getLogger("RockBlock")

    def _read(self) -> str:
        return self.s.readline().decode().strip()

    def read_next(self) -> str:
        response = self._read()
        while response is None or len(response) == 0:
            response = self._read()
        self.logger.info("-> " + response)
        return response

    def write(self, command: str):
        self.logger.info("<- " + command)
        self.s.write(command.encode())

    def write_line(self, command: str):
        self.write(command + "\r")

    def write_line_echo(self, command: str) -> bool:
        self.write_line(command)
        return self.read_next() == command

    def check_serial_connection(self) -> bool:
        if self.s is not None:
            self.s.flush()
            if self.write_line_echo("AT"):
                if self.read_next() == "OK":
                    return True
        return False

    def connect(self) -> bool:
        try:
            self.s = Serial(self.port, 19200, self.timeout)
            return self.check_serial_connection()
        except SerialException as e:
            raise RockBlockException(e)

    def disconnect(self):
        self.s.close()
        self.s = None

    @property
    def signal_quality(self) -> int:
        if self.write_line_echo("AT+CSQ"):
            output = self.read_next()
            return int(output[-1])
        raise RockBlockException("Exception getting signal quality, unexpected Serial state")

    @property
    def imei(self) -> str:
        if self.write_line_echo("AT+CGSN"):
            return self.read_next()
        raise RockBlockException("Exception getting imei, unexpected Serial state")

    @property
    def system_time(self) -> datetime:
        if self.write_line_echo("AT-MSSTM"):
            command, response = self.read_next().split(" ", 1)
            if response == "no network service":
                raise RockBlockException("Could not get system time due to no connection service")
            else:
                response_int = int(response, 16)
                return RockBlock.IRIDIUM_EPOCH + timedelta(milliseconds=response_int * 90)
