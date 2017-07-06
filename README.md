pycrafter4500
-------------

Adapted for the TI Lightcrafter 4500 from https://github.com/csi-dcsc/Pycrafter6500

DLPC350 is the controller chip on the LCR4500.

TI doc: http://www.ti.com/lit/ug/dlpu010f/dlpu010f.pdf
Doc strings adapted from dlpc350_api.cpp source code.

To connect to LCR4500, install libusb-win32 driver. Recommended way to do is this is
with [Zadig](http://zadig.akeo.ie/). The pyusb package is also required.