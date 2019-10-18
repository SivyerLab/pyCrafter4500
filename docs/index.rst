pycrafter4500
=============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   moduledoc


This is an unofficial API for some functionality of the Texas Instruments Lightcrafter 4500.

Code adapted for the TI Lightcrafter 4500 from Pycrafter6500_.

The DLPC 350 is the controller chip on the LCR 4500. TI DLPC 350 documentation can be found
on the `DLPC350 website`__.

Doc strings adapted from ``dlpc350_api.cpp`` source code.

To connect to the LCR4500, the libusb-win32 driver is required. The recommended way to do is this is
with Zadig_. The pyusb package is also required.


Install
-------

pycrafter4500 is available through pypi


::

   pip install pycrafter4500


Usage
-----

.. code-block:: python

   import pycrafter4500

Waking up from and going into standby:

.. code-block:: python

   pycrafter4500.power_up()
   pycrafter4500.power_down()

Toggling back to video mode from pattern sequence mode:

.. code-block:: python

   pycrafter4500.video_mode()

Starting a pattern sequence:

.. code-block:: python

   # for example: 222 hz, 7 bit depth, white
   pycrafter4500.pattern_mode(num_pats=3,
                              fps=222,
                              bit_depth=7,
                              led_color=0b111,  # BGR flags
                              )

If you wish to send other commands, this can be done using the ``dlpc350`` class. See source documentation for further
details.

.. code-block:: python

   from pycrafter4500 import dlpc350, connect_usb
   from pycrafter4500 import bits_to_bytes, conv_len

   with connect_usb() as lcr:
       lcr.command('w', 0x00, CMD2, CMD3, payload)


.. _Pycrafter6500: https://github.com/csi-dcsc/Pycrafter6500
.. _Zadig: http://zadig.akeo.ie/
.. _dlpc_docs: http://www.ti.com/product/DLPC350/technicaldocuments

__ dlpc_docs_
