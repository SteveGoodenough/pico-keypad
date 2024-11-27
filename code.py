# Adapted from wildestpixel gist at https://gist.github.com/wildestpixel/6b684b8bc886392f7c4c57015fab3d97

import time
import board
import busio
import usb_hid
import math

from adafruit_bus_device.i2c_device import I2CDevice
import adafruit_dotstar

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

from digitalio import DigitalInOut, Direction

cs = DigitalInOut(board.GP17)
cs.direction = Direction.OUTPUT
cs.value = 0
num_pixels = 16
pixels = adafruit_dotstar.DotStar(board.GP18, board.GP19, num_pixels, brightness=0.1, auto_write=True)
i2c = busio.I2C(board.GP5, board.GP4)
device = I2CDevice(i2c, 0x20)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
cc = ConsumerControl(usb_hid.devices)

# show startup by flashing onboard led
led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
for i in range(10):
    led.value = (i % 2) == 0
    time.sleep(0.2)

# define what the keys do; keyboard or consumer codes (like media controls)
btn_keys = [
    # top row
    {"type": "cc", "key": ConsumerControlCode.VOLUME_INCREMENT},
    {"type": "cc", "key": ConsumerControlCode.SCAN_NEXT_TRACK},
    {"type": "cc", "key": ConsumerControlCode.PLAY_PAUSE},
    {"type": "cc", "key": ConsumerControlCode.MUTE},
    # row two
    {"type": "cc", "key": ConsumerControlCode.VOLUME_DECREMENT},
    {"type": "cc", "key": ConsumerControlCode.SCAN_PREVIOUS_TRACK},
    {"type": "cc", "key": ConsumerControlCode.STOP},
    {"type": "cc", "key": ConsumerControlCode.PLAY_PAUSE},
    # row three
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.D)},  # Google Meet Mute/Unmute
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.E)},  # Google Meet Cam off/on
    {"type": "kbd", "text": "some text"},
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.W)},  # Close Chrome Tab
    # bottom row
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.X)},
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.C)},
    {"type": "kbd", "key": (Keycode.CONTROL, Keycode.V)},
    {"type": "not used", "key": None},
]

def colourwheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def read_button_states(x, y):
    pressed = [0] * num_pixels
    with device:
        device.write(bytes([0x0]))
        result = bytearray(2)
        device.readinto(result)
        b = result[0] | result[1] << 8
        for i in range(x, y):
            if not (1 << i) & b:
                pressed[i] = 1
            else:
                pressed[i] = 0
    return pressed

#def compute_z(x, y, t, pattern):
#    x = x + t
#    y = y + t
#    if pattern == 'parallel':
#        z = math.sin(x) + math.cos(x)
#    elif pattern == 'diagonal':
#        z = math.sin(x + y) + math.cos(x + y)
#    elif pattern == 'crisscross':
#        z = math.sin(x) + math.cos(y)
#    z = (z + 2) / 4
#    return z

#def hsv_to_rgb(h, s, v):
#    if s == 0.0: return (v, v, v)
#    i = int(h*6.)  # assume int() truncates!
#    f = (h*6.)-i; p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f)); i%=6
#    if i == 0: return (v, t, p)
#    if i == 1: return (q, v, p)
#    if i == 2: return (p, v, t)
#    if i == 3: return (p, q, v)
#    if i == 4: return (t, p, v)
#    if i == 5: return (v, p, q)

held = [0] * num_pixels
delta_hue = 256 // num_pixels
speed = 10  # higher numbers = faster rainbow spinning
l = 0
#patterns=['parallel', 'diagonal', 'crisscross']
lights_on = True

while True:
    no_btn = True
    pressed = read_button_states(0, num_pixels)

    for btn in range(num_pixels):
        if pressed[btn]:
            no_btn = False
            pixels[btn] = colourwheel(btn * num_pixels)  # Map pixel index to 0-255 range

            if not held[btn]:
                # print(btn, btn_keys[btn])
                if btn_keys[btn]["type"] == "cc":
                    cc.send(btn_keys[btn]["key"])
                elif btn_keys[btn]["type"] == "kbd":
                    if btn_keys[btn].get("text"):
                        layout.write(btn_keys[btn]["text"])
                    if btn_keys[btn].get("key"):
                        if type(btn_keys[btn]["key"]) is int:
                            kbd.send(btn_keys[btn]["key"])
                        else:
                            kbd.send(*btn_keys[btn]["key"])
                else:
                    lights_on = not lights_on
                held[btn] = 1

    if no_btn:  # Released state
        l = (l + 1) % 255
        for i in range(num_pixels):
            if lights_on:
                pixels[i] = colourwheel(int(l * speed + i * delta_hue) % 255)
                # pixels[i] = colourwheel((time.monotonic()*50)%255)
            else:
                pixels[i] = (0, 0, 0)  # Turn pixels off
            held[i] = 0  # Set held states to off

        # https://sandyjmacdonald.github.io/2015/01/20/leds-with-added-trigonometry/
        # TODO this takes too long to then do next key scan so figure a breakout
        #for pattern in patterns:
        #    for t in range(50):
        #        for y in range(4):
        #            for x in range(4):
        #                h = 0.1
        #                s = 1.0
        #                v = compute_z(x, y, t, pattern)
        #                rgb = hsv_to_rgb(h, s, v)
        #                r = int(rgb[0]*255.0)
        #                g = int(rgb[1]*255.0)
        #                b = int(rgb[2]*255.0)
        #                pixels[x * 4 + y] = (r, g, b)
        #                # pixels[y * 4 + x] = colourwheel(v*255.0)
        #        time.sleep(0.05)

        time.sleep(0.1)  # Debounce# Adapted from wildestpixel gist at https://gist.github.com/wildestpixel/6b684b8bc886392f7c4c57015fab3d97
