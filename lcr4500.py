import usb.core
import usb.util
import time
import numpy as np
import time
from math import floor

"""
Adapted for lcr4500 from https://github.com/csi-dcsc/Pycrafter6500

Docs: http://www.ti.com/lit/ug/dlpu010f/dlpu010f.pdf
Doc strings adapted from dlpc450_api.cpp source code

To connect to LCR4500, install libusb-win32 driver. Recommended way to do is this is
with Zadig utility (http://zadig.akeo.ie/)
"""


def conv_len(a, l):
    """
    Function that converts a number into a bit string of given length
    :param a: number to convert
    :param l: length of bit string
    :return: padded bit string
    """
    b = bin(a)[2:]
    padding = l - len(b)
    b = '0' * padding + b
    return b


def bits_to_bytes(a, reverse=True):
    """
    Function that converts bit string into a given number of bytes
    :param a: bites to convert
    :param reverse: whether or not to reverse the byte list
    :return: list of bytes
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
    Calculates desired period (us) from given fps
    :param fps: frames per second
    """
    period = floor(1.0 / fps * 10**6)
    return period


class dlpc(object):
    """
    Class representing dmd controller.
    Can connect to different DLPCs by changing product ID. Check IDs in
    device manager.
    """
    def __init__(self):
        """
        Sets up USB connection
        """
        self.dlpc = usb.core.find(idVendor=0x0451, idProduct=0x6401)
        self.dlpc.set_configuration()

        # holds answers from dlpc
        self.ans = []

    def release(self):
        """
        Release USB device
        """
        self.dlpc.reset()

    def command(self,
                mode,
                sequence_byte,
                com1,
                com2,
                data=None):
        """
        Sends a command to the dlpc
        :param mode: whether reading or writing
        :param sequence_byte:
        :param com1: command 1
        :param com2: command 3
        :param data: data to pass with command
        """
        print(hex(com1), hex(com2), end=': ')
        for i in reversed(data):
            print(hex(i), end=' ')
        print()
        # return

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

        # done writing, read feedback from dlpc
        self.ans = self.dlpc.read(0x81, 64)
        # wait a bit between commands
        time.sleep(0.02)

    def read_reply(self):
        """
        Reads in reply
        """
        for i in self.ans:
            print(hex(i))

    def standby(self):
        """
        Put the DMD into power down
        """
        self.command('w', 0x00, 0x02, 0x00, [1])

    def wakeup(self):
        """
        Wake up the DMD.
        """
        self.command('w', 0x00, 0x02, 0x00, [0])

    def change_mode(self, mode='pattern'):
        """
        Selects the input mode for the projector.
        :param mode: 0 = video mode
                     1 = pattern mode
        """
        modes = ['video', 'pattern']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x1b, [mode])

    def start_sequence(self):
        """
        Starts a pattern sequence.
        """
        self.command('w', 0x00, 0x1a, 0x24, [2])

    def pause_sequence(self):
        """
        Pauses a pattern sequence.
        """
        self.command('w', 0x00, 0x1a, 0x24, [1])

    def stop_sequence(self):
        """
        Stops a pattern sequence.
        """
        self.command('w', 0x00, 0x1a, 0x24, [0])

    def sequence_input(self, mode='video'):
        """
        Selects the input type for pattern sequence.
        :param mode: 0 = video
                     3 = flash
        """
        modes = ['video', '', '', 'flash']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x22, [mode])

    def sequence_trigger(self, mode='vsync'):
        """
        Selects the trigger type for pattern sequence.
        :param mode: 0 = vsync
        """
        modes = ['vsync']
        if mode in modes:
            mode = modes.index(mode)

        self.command('w', 0x00, 0x1a, 0x23, [mode])

    def dlpc350_set_exposure_frame_period(self,
                                          exposure_period,
                                          frame_period):
        """
        The Pattern Display Exposure and Frame Period dictates the time a pattern is exposed and the frame period.
        Either the exposure time must be equivalent to the frame period, or the exposure time must be less than the
        frame period by 230 microseconds. Before executing this command, stop the current pattern sequence. After
        executing this command, call DLPC350_ValidatePatLutData() API before starting the pattern sequence.
        (USB: CMD2: 0x1A, CMD3: 0x29)

        :param exposure_period: exposure time in microseconds (4 bytes)
        :param frame_period: frame period in microseconds (4 bytes)
        """
        exposure_period = conv_len(exposure_period, 32)
        frame_period = conv_len(frame_period, 32)

        payload = frame_period + exposure_period
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x29, payload)

    def dlpc350_set_pattern_config(self,
                                   num_lut_entries=3,
                                   to_repeat=True,
                                   num_pats_for_trig_out2=3,
                                   num_images=0):
        """
        This API controls the execution of patterns stored in the lookup table. Before using this API, stop the current
        pattern sequence using DLPC350_PatternDisplay() API. After calling this API, send the Validation command using
        the API DLPC350_ValidatePatLutData() before starting the pattern sequence.
        (USB: CMD2: 0x1A, CMD3: 0x31)

        :param num_lut_entries: number of LUT entries
        :param to_repeat: True = execute the pattern sequence once; False = repeat the pattern sequence
        :param num_pats_for_trig_out2: Number of patterns to display(range 1 through 256). If in repeat mode, then this
            value dictates how often TRIG_OUT_2 is generated
        :param num_images: Number of Image Index LUT Entries(range 1 through 64). This Field is irrelevant for Pattern
            Display Data Input Source set to a value other than internal
        """
        num_lut_entries = '0' + conv_len(num_lut_entries - 1, 7)
        to_repeat = '0000000' + str(int(to_repeat))
        num_pats_for_trig_out2 = conv_len(num_pats_for_trig_out2 - 1, 8)
        num_images = '00' + conv_len(num_images, 6)

        payload = num_images + num_pats_for_trig_out2 + to_repeat + num_lut_entries
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x31, payload)

    def dlpc350_mailbox_set_addr(self, addr=0):
        """
        This API defines the offset location within the DLPC350 mailboxes to write data into or to read data from.
        (USB: CMD2: 0x1A, CMD3: 0x32)

        :param addr: Defines the offset within the selected (opened) LUT to write/read data to/from (0-127)
        """
        addr = bits_to_bytes(conv_len(addr, 8))
        self.command('w', 0x00, 0x1a, 0x32, addr)

    def dlpc350_open_mailbox(self, mbox_num):
        """
        This API opens the specified Mailbox within the DLPC350 controller. This API must be called before sending data
        to the mailbox/LUT using DLPC350_SendPatLut() or DLPC350_SendImageLut() APIs.
        (USB: CMD2: 0x1A, CMD3: 0x33)

        :param mbox_num: 0 = Disable (close) the mailboxes
                         1 = Open the mailbox for image index configuration
                         2 = Open the mailbox for pattern definition
                         3 = Open the mailbox for the Variable Exposure
        """
        mbox_num = bits_to_bytes(conv_len(mbox_num, 8))
        self.command('w', 0x00, 0x1a, 0x33, mbox_num)

    def dlpc350_send_pat_lut(self,
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

        :param trig_type: Select the trigger type for the pattern
                          0 = Internal trigger
                          1 = External positive
                          2 = External negative
                          3 = No Input Trigger (Continue from previous; Pattern still has full exposure time)
                          0x3FF = Full Red Foreground color intensity
        :param pat_num: Pattern number (0 based index). For pattern number 0x3F, there is no pattern display. The
            maximum number supported is 24 for 1 bit-depth patterns. Setting the pattern number to be 25, with a
            bit-depth of 1 will insert a white-fill pattern. Inverting this pattern will insert a black-fill pattern.
            These patterns will have the same exposure time as defined in the Pattern Display Exposure and Frame Period
            command. Table 2-66 in the programmer's guide illustrates which bit planes are illuminated by each pattern
            number.
        :param bit_depth: Select desired bit-depth
                          0 = Reserved
                          1 = 1-bit
                          2 = 2-bit
                          3 = 3-bit
                          4 = 4-bit
                          5 = 5-bit
                          6 = 6-bit
                          7 = 7-bit
                          8 = 8-bit
        :param led_select: Choose the LEDs that are on: b0 = Red, b1 = Green, b2 = Blue
                           0 = No LED (Pass Through)
                           1 = Red
                           2 = Green
                           3 = Yellow (Green + Red)
                           4 = Blue
                           5 = Magenta (Blue + Red)
                           6 = Cyan (Blue + Green)
                           7 = White (Red + Blue + Green)
        :param do_invert_pat: True = Invert pattern
                              False = do not invert pattern
        :param do_insert_black: True = Insert black-fill pattern after current pattern. This setting requires 230 μs
                                       of time before the start of the next pattern
                                False = do not insert any post pattern
        :param do_buf_swap: True = perform a buffer swap
                            False = do not perform a buffer swap
        :param do_trig_out_prev: True = Trigger Out 1 will continue to be high. There will be no falling edge
                                        between the end of the previous pattern and the start of the current pattern.
                                        Exposure time is shared between all patterns defined under a common
                                        trigger out). This setting cannot be combined with the black-fill pattern
                                 False = Trigger Out 1 has a rising edge at the start of a pattern, and a falling edge
                                         at the end of the pattern

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

    def dlpc350_start_pat_lut_validate(self):
        """
        This API checks the programmed pattern display modes and indicates any invalid settings. This command needs to
        be executed after all pattern display configurations have been completed.
        (USB: CMD2: 0x1A, CMD3: 0x1A)
        """
        self.command('w', 0x00, 0x1a, 0x1a, bits_to_bytes(conv_len(0x00, 8)))
        print(bin(self.ans[0]))
        print('validation:', bin(self.ans[6]))


def pattern_mode(input_mode='pattern',
                 input_type='video',
                 num_pats=3,
                 trigger_type='vsync',
                 period=4500,
                 bit_depth=7,
                 led_color=0b101):

    assert bit_depth in [1, 2, 4, 7, 8]

    lcr = dlpc()

    # before proceeding to change params, need to stop pattern sequence mode
    lcr.stop_sequence()

    # 1: pattern display mode
    lcr.change_mode(input_mode)

    # 2: pattern display from external video
    lcr.sequence_input(input_type)

    # 3: setup number of luts
    lcr.dlpc350_set_pattern_config(num_lut_entries=num_pats,
                                   num_pats_for_trig_out2=num_pats)

    # 4: Pattern trigger mode selection
    lcr.sequence_trigger(trigger_type)

    # 5: Set exposure and frame rate
    lcr.dlpc350_set_exposure_frame_period(period, period)

    # 6: Skip setting up image indexes
    pass

    # 7: Set up LUT
    lcr.dlpc350_open_mailbox(2)

    bit_map = {1: [7, 15, 23],
               2: [3, 7, 11],
               4: [1, 3, 5],
               7: [0, 1, 2],
               8: [0, 1, 2]}

    for i in range(3):
        if i == 0:
            trig_type = 1
        else:
            trig_type = 2

        lcr.dlpc350_mailbox_set_addr(i)
        lcr.dlpc350_send_pat_lut(trig_type=trig_type,
                                 pat_num=bit_map[bit_depth][i],
                                 bit_depth=bit_depth,
                                 led_select=led_color)

    lcr.dlpc350_open_mailbox(0)

    # 8/9: validate
    lcr.dlpc350_start_pat_lut_validate()

    # 10: start sequence
    lcr.start_sequence()

    lcr.release()


def video_mode():
    """
    Puts LCR4500 into video mode.
    """
    lcr = dlpc()
    lcr.stop_sequence()
    lcr.change_mode('video')
    lcr.release()


if __name__ == '__main__':
    pattern_mode(input_mode='pattern',
                 input_type='video',
                 num_pats=3,
                 trigger_type='vsync',
                 period=4500,  # round() 222 hz in us
                 bit_depth=7,
                 led_color=0b010  # BGR
                 )
