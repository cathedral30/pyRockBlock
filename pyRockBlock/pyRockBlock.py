from datetime import datetime, timedelta
from serial import Serial, SerialException
from enum import Enum
import logging
import time


class RockBlockException(Exception):
    pass


class RockBlockSignalException(RockBlockException):
    pass


class SessionResponse:
    """Stores the result of an attempted GSS session."""

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
    def _get_status_message(cls, code: int, mo=True):
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
        """Returns the status message for the MO transaction."""
        return self._get_status_message(self.mo_status_code)

    @property
    def mt_status(self) -> str:
        """Returns the status message for the MT transaction."""
        return self._get_status_message(self.mt_status_code, mo=False)

    @property
    def mo_success(self) -> bool:
        """Returns true if MO data was successfully sent to the GSS."""
        if self.mo_status_code < 5:
            return True
        return False


class SbdStatus:
    """
    Stores result from SBD status requests
    """
    def __init__(self, response: str):
        s_response = response.split(", ")
        self.buffer_mo = bool(int(s_response[0].split(" ")[1]))
        self.momsn = int(s_response[1])
        self.buffer_mt = bool(int(s_response[2]))
        self.mtmsn = int(s_response[3])


class RockBlock:
    """Represents a connected RockBLOCK serial device."""

    IRIDIUM_EPOCH = datetime.fromisoformat("2014-05-11T14:23:55")

    class BufferClear(Enum):
        MO = 0
        MT = 1
        MO_MT = 2

    def __init__(self, port, timeout=5):
        self.port = port
        self.s = None
        self.timeout = timeout
        self.logger = logging.getLogger("RockBlock")
        self._modem = None
        self._imei = None

    def _read(self) -> str:
        return self.s.readline().decode().strip()

    def _read_bytes(self) -> bytes:
        return self.s.readline()

    def read_next(self) -> str:
        """
        Waits for and then returns the next non-empty line from the serial interface.

        :returns: the next message received.
        :rtype: str
        """
        response = self._read()
        while response is None or len(response) == 0:
            response = self._read()
        self.logger.info("-> " + response)
        return response

    def write(self, command: str):
        """
        Writes text to the serial interface.

        :param command: The text to write.
        :type command: str
        """
        self.logger.info("<- " + command)
        self.s.write(command.encode())

    def write_line(self, command: str):
        """
        Writes text to the serial interface followed by a return character to denote the end of a command.

        :param command: The text to write.
        :type command: str
        """
        self.write(command + "\r")

    def write_line_echo(self, command: str) -> bool:
        """
        Writes text to the serial interface followed by a return character, then waits for an echo from the device.

        :param command: The text to write.
        :type command: str

        :returns: true if an echo of the message is received.
        :rtype: bool
        """
        self.write_line(command)
        return self.read_next() == command

    def check_serial_connection(self) -> bool:
        """
        Checks if the RockBLOCK is still responding to messages via the serial interface by sending 'AT' and checking
        for an echo.

        :returns: true if the RockBLOCK is still connected to the serial interface.
        :rtype: bool
        """
        if self.s is not None:
            self.s.flush()
            if self.write_line_echo("AT"):
                if self.read_next() == "OK":
                    return True
        return False

    def connect(self) -> bool:
        """
        Attempts to connect to the RockBLOCK via the serial interface.

        :returns: true if connection is successful
        :rtype: bool
        """
        try:
            self.s = Serial(self.port, 19200, self.timeout)
            return self.check_serial_connection()
        except SerialException as e:
            raise RockBlockException(e)

    def disconnect(self):
        """Disconnects the serial connection to the RockBLOCK."""
        self.s.close()
        self.s = None

    @property
    def signal_quality(self) -> int:
        """
        Checks the network signal quality.

        :returns: integer 0-5 representing the number of ISU signal bars.
        :rtype: int
        """
        if self.write_line_echo("AT+CSQ"):
            output = self.read_next()
            return int(output[-1])
        raise RockBlockException("Exception getting signal quality, unexpected Serial state")

    @property
    def imei(self) -> str:
        """
        Gets the IMEI of the RockBLOCK modem.

        :returns: the IMEI.
        :rtype: str
        """
        if self._imei is None:
            self.write_line_echo("AT+CGSN")
            imei = self.read_next()
            if self.read_next() == "OK":
                self._imei = imei
                return imei
        else:
            return self._imei

    @property
    def modem(self) -> str:
        if self._modem is None:
            self.write_line_echo("AT+CGMM")
            modem = self.read_next()
            if self.read_next() == "OK":
                self._modem = modem
                return modem
        else:
            return self._modem

    def get_iridium_datetime(self, retry=5) -> datetime:
        """
        Gets the current Iridium SBD network datetime (UTC).

        :returns: the GSS datetime.
        :rtype: datetime
        """
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
        """
        Write text to the RockBLOCK MO buffer.

        :param message: Text to be written.
        :type message: str

        :returns: true if the text is successfully written.
        :rtype: bool
        """
        if len(message) <= 120:
            command = "AT+SBDWT=" + message
            if self.write_line_echo(command):
                if self.read_next() == "OK":
                    return True
        else:
            self.logger.error("Messages must be fewer than 120 bytes")
            return False
        raise RockBlockException("Exception queueing text")

    def queue_bytes(self, message: str) -> bool:
        """
        Write utf8 bytes to the RockBLOCK MO buffer.

        :param message: The message to be written as bytes.
        :type message: str

        :returns: true if the message is successfully written.
        :rtype: bool
        """
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
        """
        Attempts to contact the GSS, sending anything in the MO buffer and receiving MT messages.

        :returns: the response from the GSS.
        :rtype: SessionResponse
        """
        if self.write_line_echo("AT+SBDIX"):
            response = self.read_next().replace(" ", "").split(":")
            if len(response) == 2 and response[0] == "+SBDIX":
                session_response = SessionResponse(response[1])
                self.read_next()
                return session_response
        raise RockBlockException("Exception during SBD session, unexpected serial state")

    def send_text(self, message: str) -> SessionResponse:
        """
        Writes the message to the RockBLOCK MO buffer and then attempts to send to the GSS.

        :param message: Text to be sent.
        :type message: str

        :returns: the response from the GSS. (This will contain any available MT messages also)
        :rtype: SessionResponse
        """
        if self.queue_text(message):
            return self.initiate_session()
        raise RockBlockException("Exception writing text to buffer, unexpected serial state")

    def read_bytes(self) -> bytes:
        """
        Reads bytes from the RockBLOCK MT buffer.
        :return: the bytes.
        :rtype: bytes
        """
        self.write_line("AT+SBDRB")
        output = self._read_bytes()
        if self.read_next() == "OK":
            return output[15:]
        raise RockBlockException("Exception reading bytes from MT buffer")

    def read_text(self) -> str:
        """
        Reads text from the RockBLOCK MT buffer.
        :return: the text.
        :rtype: str
        """
        self.write_line("AT+SBDRT")
        output = self.read_next()
        self.read_next()
        if self.read_next() == "OK":
            return output[8:]
        raise RockBlockException("Exception reading text from MT buffer")

    def set_radio_activity(self, enabled: bool):
        """
        Disables or Enables radio activity to save power and reduce signature
        :param enabled: if radio should be active.
        """
        self.write_line_echo("AT*R" + str(int(enabled)))
        if self.read_next() == "OK":
            return
        raise RockBlockException("Exception attempting to set radio activity")

    def set_energy_used(self, energy: int):
        """
        Preset the energy accumulator value.
        :param energy: energy value in microamp hours.
        :type energy: int
        :return:
        """
        if self.write_line_echo("AT+GEMON=" + str(energy)):
            if self.read_next() == "OK":
                return
        raise RockBlockException("Failed to set energy used")

    def get_energy_used(self) -> int:
        """
        Get accumulated energy used.
        :return: energy used in microamp hours.
        :rtype: int
        """
        if self.write_line_echo("AT+GEMON"):
            response = self.read_next().split(":")

            if self.read_next() == "OK" and response[0] == "+GEMON":
                return int(response[1])
        raise RockBlockException("Failed to get energy used")

    def clear_buffer(self, clear: BufferClear):
        """
        Clear messages from the MO or MT buffer
        :param clear: MO, MT or MO_MT
        :type clear: BufferClear
        """
        if self.write_line_echo("AT+SBDD" + str(clear.value)):
            if self.read_next() == "0" and self.read_next() == "OK":
                return
        raise RockBlockException("Failed to clear buffer")

    def get_status(self) -> SbdStatus:
        """
        Get the status of the SBD modem
        :return: The SBD status
        :rtype: SbdStatus
        """
        if self.write_line_echo("AT+SBDS"):
            status = SbdStatus(self.read_next())
            if self.read_next() == "OK":
                return status
        raise RockBlockException("Failed to get SBD status")
