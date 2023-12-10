pyRockBlock Command Reference
=============================

RockBlock
=========

|
.. autoclass:: pyRockBlock.RockBlock
|

Properties
----------

|
.. autofunction:: pyRockBlock.RockBlock.signal_quality
|
.. autofunction:: pyRockBlock.RockBlock.imei
|
.. autofunction:: pyRockBlock.RockBlock.modem
|

Establishing Serial Connection
------------------------------

|
.. autofunction:: pyRockBlock.RockBlock.connect
|
.. autofunction:: pyRockBlock.RockBlock.disconnect
|
.. autofunction:: pyRockBlock.RockBlock.check_serial_connection
|

Manually Sending and Reading Serial Interface
---------------------------------------------

|
.. autofunction:: pyRockBlock.RockBlock.write
|
.. autofunction:: pyRockBlock.RockBlock.write_line
|
.. autofunction:: pyRockBlock.RockBlock.write_line_echo
|
.. autofunction:: pyRockBlock.RockBlock.read_next
|

Send and Receive SBD Messages
-----------------------------

|
.. autofunction:: pyRockBlock.RockBlock.queue_text
|
.. autofunction:: pyRockBlock.RockBlock.queue_bytes
|
.. autofunction:: pyRockBlock.RockBlock.initiate_session
|
.. autofunction:: pyRockBlock.RockBlock.send_text
|
.. autofunction:: pyRockBlock.RockBlock.read_bytes
|
.. autofunction:: pyRockBlock.RockBlock.read_text
|

Utility Commands
----------------

|
.. autofunction:: pyRockBlock.RockBlock.set_radio_activity
|
.. autofunction:: pyRockBlock.RockBlock.set_energy_used
|
.. autofunction:: pyRockBlock.RockBlock.get_energy_used
|
.. autofunction:: pyRockBlock.RockBlock.clear_buffer
|
.. autofunction:: pyRockBlock.RockBlock.get_status
|

SessionResponse
===============

|
.. autoclass:: pyRockBlock.SessionResponse
|
.. autofunction:: pyRockBlock.RockBlock.mo_status
|
.. autofunction:: pyRockBlock.RockBlock.mt_status
|
.. autofunction:: pyRockBlock.RockBlock.mo_success

SbdStatus
=========
|
.. autoclass:: pyRockBlock.SbdStatus
|
