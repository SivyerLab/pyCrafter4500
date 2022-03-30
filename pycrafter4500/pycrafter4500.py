from __future__ import print_function

import time
from contextlib import contextmanager
from math import floor

import usb.core
import usb.util
from usb.core import USBError

"""
Adapted for lcr4500 from https://github.com/csi-dcsc/Pycrafter6500

DLPC350 is the controller chip on the LCR4500.

Docs: http://www.ti.com/lit/ug/dlpu010f/dlpu010f.pdf
Doc strings adapted from dlpc350_api.cpp source code.

To connect to LCR4500, install libusb-win32 driver. Recommended way to do is this is
with Zadig utility (http://zadig.akeo.ie/)
"""

__author__  = 'Alexander Tomlinson'
__email__   = 'mexander@gmail.com'
__version__ = '0.7'


def conv_len(a, l):
    """
    Function that converts a number into a bit string of given length.

    :param int a: Number to convert.
    :param int l: Length of bit string.

    :return: Padded bit string.
    """
    b = bin(a)[2:]
    padding = l - len(b)
    b = '0' * padding + b
    return b


def bits_to_bytes(a, reverse=True):
    """
    Function that converts bit string into a given number of bytes.

    :param str a: Bytes to convert.
    :param bool reverse: Whether or not to reverse the byte list.

    :return: List of bytes.
    """
    bytelist = []

    # check if needs padding
    if len(a) % 8 != 0:
        padding = 8 - len(a) % 8
        a = '0' * padding + a

    # convert to bytes
    for i in range(len(a) // 8):
        bytelist.append(int(a[8 * i:8 * (i + 1)], 2))

    if reverse:
        bytelist.reverse()
    return bytelist


def fps_to_period(fps):
    """
    Calculates desired period (us) from given fps.

    :param int fps: Frames per second.

    :return: Period (us).
    """
    period = int(floor(1.0 / fps * 10**6))
    return period


@contextmanager
def connect_usb():
    """
    Context manager for connecting to and releasing usb device.

    :yields: USB device.
    """
    device = usb.core.find(idVendor=0x0451, idProduct=0x6401)
    device.set_configuration()

    lcr = dlpc350(device)

    yield lcr

    device.reset()
    del lcr
    del device


class dlpc350(object):
    """
    Class representing dmd controller. Can connect to different DLPCs by changing product ID. Check IDs in
    device manager.
    """
    def __init__(self, device):
        """
        Connects the device.

        :param device: lcr4500 USB device.
        """
        self.dlpc = device

    def command(self,
                mode,
                sequence_byte,
                com1,
                com2,
                data=None):
        """
        Sends a command to the dlpc.

        :param str mode: Whether reading or writing.
        :param int sequence_byte:
        :param int com1: Command 1
        :param int com2: Command 3
        :param list data: Data to pass with command.
        """

        buffer = []

        if mode == 'r':
            flagstring = 0xc0  # 0b11000000
        else:
            flagstring = 0x40  # 0b01000000

        data_len = conv_len(len(data) + 2, 16)
        data_len = bits_to_bytes(data_len)

        buffer.append(flagstring)
        buffer.append(sequence_byte)
        buffer.extend(data_len)
        buffer.append(com2)
        buffer.append(com1)

        # if data fits into single buffer, write all and fill
        if len(buffer) + len(data) < 65:
            for i in range(len(data)):
                buffer.append(data[i])

            # append empty data to fill buffer
            for i in range(64 - len(buffer)):
                buffer.append(0x00)

            self.dlpc.write(1, buffer)

        # else, keep filling buffer and pushing until data all sent
        else:
            for i in range(64 - len(buffer)):
                buffer.append(data[i])

            self.dlpc.write(1, buffer)
            buffer = []

            j = 0
            while j < len(data) - 58:
                buffer.append(data[j + 58])
                j += 1

                if j % 64 == 0:
                    self.dlpc.write(1, buffer)
                    buffer = []

            if j % 64 != 0:
                while j % 64 != 0:
                    buffer.append(0x00)
                    j += 1

                self.dlpc.write(1, buffer)

        # wait a bit between commands
        # time.sleep(0.02)
        # time.sleep(0.02)

        # done writing, read feedback from dlpc
        try:
            self.ans = self.dlpc.read(0x81, 64)
        except USBError as e:
            print('USB Error:', e)

        time.sleep(0.02)

    def read_reply(self):
        """
        Reads in reply.
        """
        for i in self.ans:
            print(hex(i))

    def get_main_status(self, pretty_print=False):
        """The Main Status command shows the status of DMD park and DLPC350 sequencer, frame buffer, and gamma
         correction.

         (USB: CMD2: 0x02, CMD3: 0x0C)
         """
        self.command('r', 0x00, 0x1a, 0x0c, [])
        if pretty_print:
            # ans = str(bin(self.ans[4]))[2:]
            ans = format(self.ans[4], '08b')
            print(f'\nDMD micromirrors are {"parked" if int(ans[-1]) else "not parked"}')
            print(f'Sequencer is {"running normally" if int(ans[-2]) else "stopped"}')
            print(f'Frame buffer is {"frozen" if int(ans[-3]) else "not frozen"}')
            print(f'Gamma correction is {"enabled" if int(ans[-4]) else "disabled"}')

    def set_power_mode(self, do_standby=False):
        """
        The Power Control places the DLPC350 in a low-power state and powers down the DMD interface. Standby mode should
        only be enabled after all data for the last frame to be displayed has been transferred to the DLPC350. Standby
        mode must be disabled prior to sending any new data.

        (USB: CMD2: 0x02, CMD3: 0x00)

        :param bool do_standby:
            :True: Standby mode. Places DLPC350 in low power state and powers down the DMD interface.
            :False: Normal operation. The selected external source will be displayed.
        """
        do_standby = int(do_standby)
        self.command('w', 0x00, 0x02, 0x00, [do_standby])

    def start_pattern_lut_validate(self):
        """
        This API checks the programmed pattern display modes and indicates any invalid settings. This command needs to
        be executed after all pattern display configurations have been completed.

        (USB: CMD2: 0x1A, CMD3: 0x1A)
        """
        self.command('w', 0x00, 0x1a, 0x1a, bits_to_bytes(conv_len(0x00, 8)))

    def set_dmd_park(self, park=False):
        """
        This command is used to park or unpark the DMD, whenever system is idle user can send this command to park the
        DMD.

        (USB: CMD2: 0x06, CMD3: 0x09)

        :param bool park: Whether to park the dmd mirrors
        """
        park = int(park)
        self.command('w', 0x00, 0x06, 0x09, [park])

    def set_buffer_freeze(self, freeze=False):
        """
        The Display Buffer Freeze command disables swapping the memory buffers.

        (USB: CMD2: 0x10, CMD3: 0x0A)

        :param bool park: Whether to park the dmd mirrors
        """
        park = int(freeze)
        self.command('w', 0x00, 0x10, 0x0a, [freeze])

    def set_display_mode(self, mode='pattern'):
        """
        Selects the input mode for the projector.

        (USB: CMD2: 0x1A, CMD3: 0x1B)

        :param int mode:
            :0: "video" mode
            :1: "pattern" mode
        """
        modes = ['video', 'pattern']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x1b, [mode])

    def set_pattern_input_source(self, mode='video'):
        """
        Selects the input type for pattern sequence.

        (USB: CMD2: 0x1A, CMD3: 0x22)

        :param int mode:
            :0: "video"
            :3: "flash"
        """
        modes = ['video', '', '', 'flash']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x22, [mode])

    def set_pattern_trigger_mode(self, mode='vsync'):
        """
        Selects the trigger type for pattern sequence.

        (USB: CMD2: 0x1A, CMD3: 0x23)

        :param int mode:
            :0: "vsync"
        """
        modes = ['vsync']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x23, [mode])

    def set_gamma_correction(self, apply_gamma=True):
        """
        This command only works in video mode.

        Because the DMD is inherently linear in response, the Gamma Correction command specifies the removal of the
        gamma curve that is applied to the video data at the source. Two degamma tables are provided: TI Video
        (Enhanced) and TI Video (Max Brightness).

        (USB: CMD2: 0x1A, CMD3: 0x0E)

        :param bool apply_gamma: Whether to apply gamma correction while in video mode.
        """
        if apply_gamma:
            apply_gamma = '10000000'
        else:
            apply_gamma = '00000000'
        self.command('w', 0x00, 0x1a, 0x0e, bits_to_bytes(apply_gamma))

    def pattern_display(self, action='start'):
        """
        This API starts or stops the programmed patterns sequence.

        (USB: CMD2: 0x1A, CMD3: 0x24)

        :param int action: Pattern Display Start/Stop Pattern Sequence

            :0: Stop Pattern Display Sequence. The next "Start" command will restart the pattern sequence from the
               beginning.
            :1: Pause Pattern Display Sequence. The next "Start" command will start the pattern sequence by
               re-displaying the current pattern in the sequence.
            :2: Start Pattern Display Sequence.
        """
        actions = ['stop', 'pause', 'start']
        if action in actions:
            action = actions.index(action)

        self.command('w', 0x00, 0x1a, 0x24, [action])

    def set_exposure_frame_period(self,
                                  exposure_period,
                                  frame_period):
        """
        The Pattern Display Exposure and Frame Period dictates the time a pattern is exposed and the frame period.
        Either the exposure time must be equivalent to the frame period, or the exposure time must be less than the
        frame period by 230 microseconds. Before executing this command, stop the current pattern sequence. After
        executing this command, call ``DLPC350_ValidatePatLutData()`` API before starting the pattern sequence.

        (USB: CMD2: 0x1A, CMD3: 0x29)

        :param int exposure_period: Exposure time in microseconds (4 bytes).
        :param int frame_period: Frame period in microseconds (4 bytes).
        """
        exposure_period = conv_len(exposure_period, 32)
        frame_period = conv_len(frame_period, 32)

        payload = frame_period + exposure_period
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x29, payload)

    def set_pattern_config(self,
                           num_lut_entries=3,
                           do_repeat=True,
                           num_pats_for_trig_out2=3,
                           num_images=0):
        """
        This API controls the execution of patterns stored in the lookup table. Before using this API, stop the current
        pattern sequence using ``DLPC350_PatternDisplay()`` API. After calling this API, send the Validation command
        using the API DLPC350_ValidatePatLutData() before starting the pattern sequence.

        (USB: CMD2: 0x1A, CMD3: 0x31)

        :param int num_lut_entries: Number of LUT entries.
        :param bool do_repeat:

            :True: Execute the pattern sequence once.
            :False: Repeat the pattern sequence.

        :param int num_pats_for_trig_out2: Number of patterns to display(range 1 through 256). If in repeat mode, then
           this value dictates how often TRIG_OUT_2 is generated.

        :param int num_images: Number of Image Index LUT Entries(range 1 through 64). This Field is irrelevant for Pattern
            Display Data Input Source set to a value other than internal.
        """
        num_lut_entries = '0' + conv_len(num_lut_entries - 1, 7)
        do_repeat = '0000000' + str(int(do_repeat))
        num_pats_for_trig_out2 = conv_len(num_pats_for_trig_out2 - 1, 8)
        num_images = '00' + conv_len(num_images, 6)

        payload = num_images + num_pats_for_trig_out2 + do_repeat + num_lut_entries
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x31, payload)

    def mailbox_set_address(self, address=0):
        """
        This API defines the offset location within the DLPC350 mailboxes to write data into or to read data from.

        (USB: CMD2: 0x1A, CMD3: 0x32)

        :param int address: Defines the offset within the selected (opened) LUT to write/read data to/from (0-127).
        """
        address = bits_to_bytes(conv_len(address, 8))
        self.command('w', 0x00, 0x1a, 0x32, address)

    def open_mailbox(self, mbox_num):
        """
        This API opens the specified Mailbox within the DLPC350 controller. This API must be called before sending data
        to the mailbox/LUT using DLPC350_SendPatLut() or DLPC350_SendImageLut() APIs.

        (USB: CMD2: 0x1A, CMD3: 0x33)

        :param mbox_num:
            :0: Disable (close) the mailboxes.
            :1: Open the mailbox for image index configuration.
            :2: Open the mailbox for pattern definition.
            :3: Open the mailbox for the Variable Exposure.
        """
        mbox_num = bits_to_bytes(conv_len(mbox_num, 8))
        self.command('w', 0x00, 0x1a, 0x33, mbox_num)

    def send_pattern_lut(self,
                         trig_type,
                         pat_num,
                         bit_depth,
                         led_select,
                         do_invert_pat=False,
                         do_insert_black=False,
                         do_buf_swap=False,
                         do_trig_out_prev=False):
        """
        Mailbox content to setup pattern definition. See table 2-65 in programmer's guide for detailed description of
        pattern LUT entries.

        (USB: CMD2: 0x1A, CMD3: 0x34)

        :param int trig_type: Select the trigger type for the pattern

            :0: Internal trigger.
            :1: External positive.
            :2: External negative.
            :3: No Input Trigger (Continue from previous; Pattern still has full exposure time).
            :0x3FF: Full Red Foreground color intensity

        :param int pat_num: Pattern number (0 based index). For pattern number ``0x3F``, there is no pattern display. The
            maximum number supported is 24 for 1 bit-depth patterns. Setting the pattern number to be 25, with a
            bit-depth of 1 will insert a white-fill pattern. Inverting this pattern will insert a black-fill pattern.
            These patterns will have the same exposure time as defined in the Pattern Display Exposure and Frame Period
            command. Table 2-66 in the programmer's guide illustrates which bit planes are illuminated by each pattern
            number.

        :param bit_depth: Select desired bit-depth

            :0: Reserved
            :1: 1-bit
            :2: 2-bit
            :3: 3-bit
            :4: 4-bit
            :5: 5-bit
            :6: 6-bit
            :7: 7-bit
            :8: 8-bit

        :param int led_select: Choose the LEDs that are on (bit flags b0 = Red, b1 = Green, b2 = Blue)

            :0: 0b000 No LED (Pass through)
            :1: 0b001 Red
            :2: 0b010 Green
            :3: 0b011 Yellow (Green + Red)
            :4: 0b100 Blue
            :5: 0b101 Magenta (Blue + Red)
            :6: 0b110 Cyan (Blue + Green)

        :param bool do_invert_pat:
            :True: Invert pattern.
            :False: Do not invert pattern.

        :param bool do_insert_black:
            :True: Insert black-fill pattern after current pattern. This setting requires 230 us of time before the
               start of the next pattern.
            :False: Do not insert any post pattern.

        :param bool do_buf_swap:
            :True: perform a buffer swap.
            :False: Do not perform a buffer swap.

        :param do_trig_out_prev:
            :True: Trigger Out 1 will continue to be high. There will be no falling edge between the end of the
               previous pattern and the start of the current pattern. Exposure time is shared between all patterns
               defined under a common trigger out). This setting cannot be combined with the black-fill pattern.
            :False: Trigger Out 1 has a rising edge at the start of a pattern, and a falling edge at the end of the
               pattern.

        """
        # byte 0
        trig_type = conv_len(trig_type, 2)
        pat_num = conv_len(pat_num, 6)

        byte_0 = pat_num + trig_type

        # byte 1
        bit_depth = conv_len(bit_depth, 4)
        led_select = conv_len(led_select, 4)

        byte_1 = led_select + bit_depth

        # byte 2
        do_invert_pat = str(int(do_invert_pat))
        do_insert_black = str(int(do_insert_black))
        do_buf_swap = str(int(do_buf_swap))
        do_trig_out_prev = str(int(do_trig_out_prev))

        byte_2 = '0000' + do_trig_out_prev + do_buf_swap + do_insert_black + do_invert_pat

        payload = byte_2 + byte_1 + byte_0
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x34, payload)


def pattern_mode(input_mode='pattern',
                 input_type='video',
                 num_pats=3,
                 trigger_type='vsync',
                 period=fps_to_period(222),
                 bit_depth=7,
                 led_color=0b111,  # BGR
                 **kwargs
                 ):
    """
    Helper function to setup a video pattern mode.

    :param str input_mode: See :meth:`pycrafter4500.set_display_mode`
    :param str input_type: See :meth:`pycrafter4500.set_pattern_input_source`
    :param int num_pats: See :meth:`pycrafter4500.set_pattern_config`
    :param str trigger_type: See :meth:`pycrafter4500.set_pattern_trigger_mode`
    :param int period: See :meth:`pycrafter4500.set_exposure_frame_period`
    :param int bit_depth: See :meth:`pycrafter4500.send_pattern_lut`
    :param int led_color: See :meth:`pycrafter4500.send_pattern_lut`
    """

    if 'fps' in kwargs:
        period = fps_to_period(kwargs['fps'])

    with connect_usb() as lcr:
        assert bit_depth in [1, 2, 4, 7, 8]

        # before proceeding to change params, need to stop pattern sequence mode
        lcr.pattern_display('stop')

        # 1: pattern display mode
        lcr.set_display_mode(input_mode)

        # 2: pattern display from external video
        lcr.set_pattern_input_source(input_type)

        # 3: setup number of luts
        lcr.set_pattern_config(num_lut_entries=num_pats,
                               num_pats_for_trig_out2=num_pats)

        # 4: Pattern trigger mode selection
        lcr.set_pattern_trigger_mode(trigger_type)

        # 5: Set exposure and frame rate
        lcr.set_exposure_frame_period(period, period)

        # 6: Skip setting up image indexes
        pass

        # 7: Set up LUT
        lcr.open_mailbox(2)

        bit_map = {1: [7, 15, 23],
                   2: [3, 7, 11],
                   4: [1, 3, 5],
                   7: [0, 1, 2],
                   8: [0, 1, 2]}

        for i in range(3):
            if i == 0:
                trig_type = 1
            else:
                trig_type = 3

            lcr.mailbox_set_address(i)
            lcr.send_pattern_lut(trig_type=trig_type,
                                 pat_num=bit_map[bit_depth][i],
                                 bit_depth=bit_depth,
                                 led_select=led_color)

        lcr.open_mailbox(0)

        # 8/9: validate
        lcr.start_pattern_lut_validate()

        # 10: start sequence
        lcr.pattern_display('start')
        # idk why you need a second start coming out of video mode
        lcr.pattern_display('start')


def video_mode():
    """
    Puts LCR4500 into video mode.
    """
    with connect_usb() as lcr:
        lcr.pattern_display('stop')
        lcr.set_display_mode('video')


def power_down():
    """
    Puts LCR4500 into standby mode.
    """
    with connect_usb() as lcr:
        lcr.pattern_display('stop')
        lcr.set_power_mode(do_standby=True)


def power_up():
    """
    Wakes LCR4500 up from standby mode.
    """
    with connect_usb() as lcr:
        lcr.set_power_mode(do_standby=False)


def set_gamma(value):
    """
    Sets gamma.
    """
    with connect_usb() as lcr:
        lcr.set_gamma_correction(apply_gamma=value)
        lcr.get_main_status(True)
