from datetime import datetime, timedelta
from serial import Serial, SerialException
import time
import logging


class RockBlockException(Exception):
    pass


class RockBlockSignalException(RockBlockException):
    pass


class SessionResponse:

    MO_STATUS_CODES = {
        0: "MO Success",
        1: "MO Success, MT too big for transfer",
        2: "MO Success, location update not accepted",
        3: "MO Success",
        4: "MO Success",
        5: "MO Failure",
        6: "MO Failure",
        7: "MO Failure",
        8: "MO Failure",
        9: "Unknown",
        10: "GSS reports call did not complete in allowed time",
        11: "MO message queue full at GSS",
        12: "MO message has too many segments",
        13: "GSS reports session did not complete",
        14: "Invalid segment size",
        15: "Access is denied",
        16: "ISU has been locked and may not make SBD calls",
        17: "Gateway not responding",
        18: "Connection lost",
        19: "Link failure",
        32: "No network service",
        33: "Antenna fault",
        34: "Radio is disabled",
        35: "ISU is busy",
        36: "Try later, must wait 3 minutes since last registration",
        37: "SBD service is temporarily disabled",
        38: "Try later, traffic management period",
        64: "Band violation",
        65: "PLL lock failure, hardware error during attempted transmit"
    }

    MT_STATUS_CODES = {
        0: "No SBD message to receive from the GSS",
        1: "SBD message successfully received from the GSS",
        2: "An error occurred while attempting to perform a mailbox check or receive a message from the GSS"
    }

    @classmethod
    def get_status_message(cls, code: int, mo=True):
        if mo:
            try:
                return cls.MO_STATUS_CODES[code]
            except IndexError:
                return "Failure (reserved)"
        else:
            return cls.MT_STATUS_CODES[code]

    def __init__(self, response: str):

        response_values = response.split(",")

        self.mo_status_code = int(response_values[0])
        self.momsn = response_values[1]
        self.mt_status_code = int(response_values[2])
        self.mtmsn = response_values[3]
        self.mt_length = int(response_values[4])
        self.mt_queued = int(response_values[5])

    @property
    def mo_status(self) -> str:
        return self.get_status_message(self.mo_status_code)

    @property
    def mt_status(self) -> str:
        return self.get_status_message(self.mt_status_code, mo=False)

    @property
    def mo_success(self) -> bool:
        if self.mo_status_code < 5:
            return True
        return False


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

    def get_iridium_datetime(self, retry=5) -> datetime:
        if self.write_line_echo("AT-MSSTM"):
            command, response = self.read_next().split(" ", 1)
            if response == "no network service":
                self.read_next()
                if retry > 0:
                    self.logger.warning("No signal... retrying")
                    time.sleep(1)
                    return self.get_iridium_datetime(retry - 1)
                else:
                    raise RockBlockSignalException("Could not get system time due to no signal")
            else:
                response_int = int(response, 16)
                return RockBlock.IRIDIUM_EPOCH + timedelta(milliseconds=response_int * 90)
        raise RockBlockException("Exception getting system time, unexpected Serial state")

    def queue_text(self, message: str) -> bool:
        if len(message) <= 120:
            command = "AT+SBDWT=" + message
            if self.write_line_echo(command):
                if self.read_next() == "OK":
                    return True
        else:
            self.logger.error("Messages must be fewer than 120 bytes")
            return False

    def queue_bytes(self, message: str) -> bool:
        if 1 > len(message) > 340:
            raise RockBlockException("Invalid number of bytes to send")

        if self.write_line_echo("AT+SBDWB=" + str(len(message))):

            if self.read_next() == "READY":
                checksum = 0

                for c in message:
                    checksum += ord(c)

                command_bytes = message.encode() + bytes([checksum >> 8]) + bytes([checksum & 0xFF])
                self.s.write(command_bytes)
                if self.read_next() == "0" and self.read_next() == "OK":
                    return True
                else:
                    return False
        raise RockBlockException("Exception writing bytes to buffer, unexpected serial state")

    def initiate_session(self) -> SessionResponse:
        if self.write_line_echo("AT+SBDIX"):
            response = self.read_next().replace(" ", "").split(":")
            if len(response) == 2 and response[0] == "+SBDIX":
                return SessionResponse(response[1])
        raise RockBlockException("Exception during SBD session, unexpected serial state")

    def send_text(self, message: str) -> SessionResponse:
        if self.queue_text(message):
            return self.initiate_session()
        raise RockBlockException("Exception writing text to buffer, unexpected serial state")
