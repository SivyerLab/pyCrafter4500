![version_badge] ![downloads_badge] ![license_badge]

# pycrafter4500

This is an unofficial API for some functionality of the Texas Instruments Lightcrafter 4500.

Code adapted for the TI Lightcrafter 4500 from https://github.com/csi-dcsc/Pycrafter6500

The DLPC 350 is the controller chip on the LCR 4500.

TI DLPC 350 documentation can be found at: http://www.ti.com/product/DLPC350/technicaldocuments

Doc strings adapted from dlpc350_api.cpp source code.

To connect to the LCR4500, the libusb-win32 driver is required. The recommended way to do is this is
with [Zadig](http://zadig.akeo.ie/). The pyusb package is also required.


## Install

pycrafter4500 is available through pypi

```bash
pip install pycrafter4500
```


## Usage

```python
import pycrafter4500
```

Waking up from and going into standby:

```python
pycrafter4500.power_up()
pycrafter4500.power_down()
```

Toggling back to video mode from pattern sequence mode:

```python
pycrafter4500.video_mode()
```

Starting a pattern sequence:

```python
# for example: 222 hz, 7 bit depth, white
pycrafter4500.pattern_mode(num_pats=3,
                           fps=222,
                           bit_depth=7,
                           led_color=0b111,  # BGR flags                 
                           )
```

If you wish to send other commands, this can be done using the dlpc350 class. See source documentation for further details.

```python
from pycrafter4500 import dlpc350, connect_usb
from pycrafter4500 import bits_to_bytes, conv_len

with connect_usb() as lcr:
    lcr.command('w', 0x00, CMD2, CMD3, payload)
```

  [version_badge]: https://img.shields.io/pypi/v/pycrafter4500.svg
  [downloads_badge]: https://img.shields.io/pypi/dm/pycrafter4500.svg
  [license_badge]: https://img.shields.io/github/license/SivyerLab/pyCrafter4500.svg
