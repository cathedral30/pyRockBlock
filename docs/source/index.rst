.. pyRockBlock documentation master file, created by
   sphinx-quickstart on Mon Nov 13 16:29:34 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyRockBlock's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Requirements
============
- Python 3.6 and newer

Installation
============

This installs a package that can be used from Python (``import pyRockBlock``).

To install for all users on the system, administrator rights (root)
may be required.

From PyPI
---------
pyRockBlock can be installed from PyPI::

    python -m pip install pyRockBlock

Connecting to your RockBLOCK
============================

Once your rockBLOCK has been connected to your device via USB you will need to find its local address.

Linux / macOS
-------------

List all local devices::

    ls /dev/tty*

The name will vary depending on machine but will generally include USB in the name (e.g. ``/dev/ttyUSB0`` or ``/dev/tty.usbserial-FTH9I1S5``)

Windows
----------

List COM devices::

    mode

When connected to my machine the port was ``COM6`` but this will vary, it can be helpful to run the command before connecting to see what port becomes active.

Starting pyRockBLOCK
--------------------

Once you have the address of your device, create an instance of RockBlock and call the connect method::

    from pyRockBlock import RockBlock

    rb = RockBlock(<device address>)
    rb.connect()
