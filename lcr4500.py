import usb.core
import usb.util
import time
import numpy as np
import time

"""
https://github.com/csi-dcsc/Pycrafter6500

doc: http://www.ti.com/lit/ug/dlpu010f/dlpu010f.pdf
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


def bits_to_bytes(a):
    """
    Function that converts bit string into a given number of bytes
    :param a: bites to convert
    :return: bytes
    """
    bytelist = []

    # check if needs padding
    if len(a) % 8 != 0:
        padding = 8 - len(a) % 8
        a = '0' * padding + a

    # convert to bytes
    for i in range(len(a) // 8):
        bytelist.append(int(a[8 * i:8 * (i + 1)], 2))

    bytelist.reverse()
    return bytelist


class dlpc(object):
    """
    Class representing dmd controller.
    Can connect to different DLPCs by changing product ID. Check hardware ID in
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
        :return:
        """
        self.dlpc.reset()

    def command(self, mode, sequence_byte, com1, com2, data=None):
        """
        Sends a command to the dlpc
        :param mod: whether reading or writing
        :param sequence_byte:
        :param com1:
        :param com2:
        :param data: data for command
        :return:
        """
        buffer = []

        flagstring = '1' if mode == 'r' else '0'
        flagstring += '1000000'
        flagstring = bits_to_bytes(flagstring)[0]

        data_len = conv_len(len(data) + 2, 16)
        data_len = bits_to_bytes(data_len)

        buffer.append(flagstring)
        buffer.append(sequence_byte)
        buffer.append(data_len[0])
        buffer.append(data_len[1])
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

    def check_for_errors(self):
        """"
        Checks response for errors
        """
        self.command('r', 0x22, 0x01, 0x00, [])
        if self.ans[6] != 0:
            print(self.ans[6])

    def read_reply(self):
        """
        Reads in reply
        """
        for i in self.ans:
            print(hex(i))

    def standby(self):
        """
        Put the dmd into power down
        """
        self.command('w', 0x00, 0x02, 0x00, [1])
        # self.check_for_errors()

    def wakeup(self):
        """
        Put the dmd into power down
        """
        self.command('w', 0x00, 0x02, 0x00, [0])
        # self.check_for_errors()

    def change_mode(self, mode):
        # 0 is video
        # 1 is pattern
        self.command('w', 0x00, 0x1a, 0x1b, [mode])
        # self.check_for_errors()

    def start_sequence(self):
        """
        Starts a pattern sequence
        """
        self.command('w', 0x00, 0x1a, 0x24, [2])
        # self.check_for_errors()

    def pause_sequence(self):
        """
        Starts a pattern sequence
        """
        self.command('w', 0x00, 0x1a, 0x24, [1])
        # self.check_for_errors()

    def stop_sequence(self):
        """
        Starts a pattern sequence
        """
        self.command('w', 0x00, 0x1a, 0x24, [0])
        # self.check_for_errors()

    def sequence_input(self, mode=0):
        """
        Selects the input type for pattern sequence
        :param mode: 0 is video, 3 is flash
        :return:
        """
        self.command('w', 0x00, 0x1a, 0x22, [mode])

    def sequence_trigger(self, mode=0):
        """
        Selects the trigger type for pattern sequence
        :param mode: 0 is VSYNC
        """
        self.command('w', 0x00, 0x1a, 0x23, [mode])

    def sequence_exp_per(self, exp, per):
        """
        Selects the exposure and frame period for the pattern sequence
        :param exp: pattern exposure time (us, 4 bytes)
        :param per: frame period (us, 4 bytes)
        """
        exp = conv_len(exp, 32)
        per = conv_len(per, 32)

        payload = exp + per
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x29, payload)

    def sequence_control(self, num_lut=2, to_repeat=True, num_patterns=2, num_flash=0):
        """
        TBD
        :param num_lut:
        :param to_repeat: whether or not the pattern sequence repeats, bool
        :param num_patterns:
        :param _:
        :return:
        """
        num_lut = conv_len(num_lut, 7) + '0'
        to_repeat = str(int(to_repeat)) + '0000000'
        num_patterns = conv_len(num_patterns, 8)
        num_flash = conv_len(num_flash, 6) + '00'

        payload = num_lut + to_repeat + num_patterns + num_flash
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x31, payload)

    def mailbox_setup(self, value):
        """
        Mailbox to send data to appropriate registers
        :param value:
        0 = Disable (close) the mailboxes
        1 = Open the mailbox for image index configuration
        2 = Open the mailbox for pattern definition
        3 = Open the mailbox for variable exposure pattern definition
        """
        value = bits_to_bytes(conv_len(value, 8))
        self.command('w', 0x00, 0x1a, 0x33, value)

    def pattern_setup(self, trigger, pattern_number, bit_depth, leds, do_invert, do_clear_dmd, do_swap, do_trigger):
        """
        Mailbox content to setup pattern definition
        :param trigger:
        :param pattern_number:
        :param bit_depth:
        :param leds:
        :param do_invert:
        :param clear_dmd:
        :param do_swap:
        :param do_trigger:
        :return:
        """
        # byte 0
        trigger = conv_len(trigger, 2)
        pattern_number = conv_len(pattern_number, 6)

        byte_0 = trigger + pattern_number

        # byte 1
        bit_depth = conv_len(bit_depth, 4)
        leds = conv_len(leds, 4)

        byte_1 = bit_depth + leds

        # byte 2
        do_invert = str(int(do_invert))
        do_clear_dmd = str(int(do_clear_dmd))
        do_swap = str(int(do_swap))
        do_trigger = str(int(do_trigger))

        byte_2 = do_invert + do_clear_dmd + do_swap + do_trigger + '0000'

        payload = byte_0 + byte_1 + byte_2
        payload = bits_to_bytes(payload)

        self.command('w', 0x00, 0x1a, 0x34, payload)

    def validate(self):
        """
        Validates the pattern sequence
        :return:
        """
        self.command('w', 0x00, 0x1a, 0x1a, bits_to_bytes(conv_len(0, 8)))
        print(bin(self.ans[0]))


def pattern_mode():
    lcr = dlpc()

    # 1: pattern display mode
    lcr.change_mode(1)
    time.sleep(0.1)

    # before proceeding to change params, need to stop pattern sequence mode
    lcr.stop_sequence()
    time.sleep(0.1)

    # 2: pattern display from external video
    lcr.sequence_input(0)
    time.sleep(0.1)

    # 3: setup number of luts?
    lcr.sequence_control(1, True, 2)
    time.sleep(0.1)

    # 4: Pattern trigger mode selection
    lcr.sequence_trigger(0)
    time.sleep(0.1)

    # 5: Set exposure and frame rate
    lcr.sequence_exp_per(4500, 4500)
    time.sleep(0.1)

    # 6: Skip setting up image indexes
    pass

    # 7: Set up LUT
    # lcr.mailbox_setup(2)
    lcr.pattern_setup(0b00, 0, 7, 0b111, False, False, False, False)
    time.sleep(0.1)
    # lcr.pattern_setup(0b00, 1, 7, 0b001, False, False, False, False)
    time.sleep(0.1)
    # lcr.pattern_setup(0b00, 2, 7, 0b001, False, False, False, False)
    time.sleep(0.1)
    # lcr.mailbox_setup(0)
    time.sleep(0.1)

    # 8/9: validate
    lcr.validate()
    time.sleep(0.1)

    # 10: start sequence
    lcr.start_sequence()
    time.sleep(0.1)

    lcr.release()



