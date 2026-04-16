"""
Hardware Interface for Raspberry Pi
4x4 Keypad + Nokia 5110 (PCD8544) LCD

Pin Mapping (BCM GPIO):
=================== Nokia 5110 LCD ====================
| LCD Pin | Function | Raspberry Pi | BCM GPIO |
|---------|----------|--------------|----------|
| VCC     | 3.3V     | Pin 1        | -        |
| GND     | Ground   | Pin 6        | -        |
| SCE     | Chip Sel | Pin 15       | GPIO 22  |
| RST     | Reset    | Pin 16       | GPIO 23  |
| D/C     | Data/Cmd | Pin 13       | GPIO 27  |
| MOSI    | SPI MOSI | Pin 12       | GPIO 18  |
| SCLK    | SPI CLK  | Pin 11       | GPIO 17  |
| LED     | Backlight| Pin 33       | GPIO 13  |

=================== 4x4 Keypad ====================
Rows = OUTPUT, Columns = INPUT (with pull-down)

| Row/Col | BCM GPIO | Physical Pin |
|---------|----------|--------------|
| R1      | GPIO 19  | Pin 35       |
| R2      | GPIO 26  | Pin 37       |
| R3      | GPIO 20  | Pin 38       |
| R4      | GPIO 21  | Pin 40       |
| C1      | GPIO 16  | Pin 36       |
| C2      | GPIO 12  | Pin 32       |
| C3      | GPIO 25  | Pin 22       |
| C4      | GPIO 24  | Pin 18       |
"""

import RPi.GPIO as GPIO
import spidev
import time
import threading
from datetime import datetime
import logging

logging.basicConfig(
    filename='key_strokes.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

DEBUG = True

def log(msg):
    if DEBUG:
        print(f"[LCD] {msg}")

LCD_SCE = 22   # GPIO 22 - Chip Select
LCD_RST = 23   # GPIO 23 - Reset
LCD_DC = 27    # GPIO 27 - Data/Command
LCD_MOSI = 18  # GPIO 18 - SPI MOSI
LCD_SCLK = 17  # GPIO 17 - SPI Clock
LCD_LED = 13   # GPIO 13 - Backlight

KEYPAD_ROW_PINS = [19, 26, 20, 21]   # R1, R2, R3, R4
KEYPAD_COL_PINS = [16, 12, 25, 24]   # C1, C2, C3, C4

KEY_MAP = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

LCD_WIDTH = 84
LCD_HEIGHT = 48

FONT_5X7 = {
    'A': [0x00,0x7C,0x11,0x11,0x7F,0x11,0x11],
    'B': [0x00,0x7F,0x11,0x1F,0x11,0x1F,0x11],
    'C': [0x00,0x3E,0x41,0x41,0x41,0x41,0x22],
    'D': [0x00,0x7F,0x41,0x41,0x41,0x3E,0x00],
    'E': [0x00,0x7F,0x11,0x1F,0x11,0x11,0x00],
    'F': [0x00,0x7F,0x11,0x1F,0x11,0x01,0x01],
    'G': [0x00,0x3E,0x41,0x41,0x5F,0x41,0x22],
    'H': [0x00,0x7F,0x11,0x11,0x7F,0x11,0x11],
    'I': [0x00,0x41,0x41,0x7F,0x41,0x41,0x00],
    'J': [0x00,0x21,0x41,0x41,0x7F,0x01,0x00],
    'K': [0x00,0x7F,0x11,0x11,0x27,0x25,0x23],
    'L': [0x00,0x7F,0x01,0x01,0x01,0x01,0x00],
    'M': [0x00,0x7F,0x04,0x08,0x04,0x7F,0x00],
    'N': [0x00,0x7F,0x08,0x04,0x02,0x7F,0x00],
    'O': [0x00,0x3E,0x41,0x41,0x41,0x41,0x3E],
    'P': [0x00,0x7F,0x11,0x11,0x7F,0x01,0x01],
    'Q': [0x00,0x3E,0x41,0x41,0x22,0x5D,0x00],
    'R': [0x00,0x7F,0x11,0x19,0x27,0x25,0x23],
    'S': [0x00,0x26,0x49,0x49,0x49,0x32,0x00],
    'T': [0x00,0x01,0x01,0x7F,0x01,0x01,0x00],
    'U': [0x00,0x3F,0x01,0x01,0x01,0x3F,0x00],
    'V': [0x00,0x07,0x03,0x01,0x03,0x07,0x00],
    'W': [0x00,0x3F,0x01,0x04,0x01,0x3F,0x00],
    'X': [0x00,0x33,0x15,0x0D,0x15,0x33,0x00],
    'Y': [0x00,0x03,0x05,0x79,0x05,0x03,0x00],
    'Z': [0x00,0x31,0x29,0x25,0x21,0x31,0x00],
    ' ': [0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '0': [0x00,0x3E,0x43,0x45,0x49,0x51,0x3E],
    '1': [0x00,0x00,0x21,0x7F,0x01,0x00,0x00],
    '2': [0x00,0x21,0x43,0x45,0x49,0x31,0x00],
    '3': [0x00,0x22,0x41,0x49,0x49,0x36,0x00],
    '4': [0x00,0x0C,0x14,0x24,0x7F,0x04,0x00],
    '5': [0x00,0x26,0x49,0x49,0x49,0x32,0x00],
    '6': [0x00,0x3E,0x49,0x49,0x49,0x32,0x00],
    '7': [0x00,0x01,0x01,0x79,0x05,0x03,0x00],
    '8': [0x00,0x36,0x49,0x49,0x49,0x36,0x00],
    '9': [0x00,0x26,0x49,0x49,0x49,0x3E,0x00],
    '*': [0x00,0x00,0x24,0x18,0x18,0x24,0x00],
    '#': [0x00,0x14,0x7F,0x14,0x7F,0x14,0x00],
}

class Nokia5110LCD:
    def __init__(self, spi_channel=0):
        self.spi_channel = spi_channel
        self.spi = None
        self.font = {}
        
    def init(self):
        log("Starting LCD init...")
        GPIO.setup(LCD_SCE, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(LCD_RST, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(LCD_DC, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(LCD_LED, GPIO.OUT, initial=GPIO.HIGH)
        log("GPIO pins configured")
        
        log("Opening SPI device...")
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 4000000  # Higher speed like working examples
        self.spi.mode = 0
        log("SPI opened")
        
        time.sleep(0.1)
        log("Toggling RST...")
        GPIO.output(LCD_RST, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(LCD_RST, GPIO.HIGH)
        time.sleep(0.01)
        
        log("Sending init commands...")
        self.write_command(0x21)
        self.write_command(0x90)  # Lower contrast - try 0x80-0xC0
        self.write_command(0x04)
        self.write_command(0x14)
        self.write_command(0x20)
        time.sleep(0.1)
        self.clear()
        self.write_command(0x0C)
        time.sleep(0.1)
        
        log("LCD init complete!")
        
    def write_command(self, cmd):
        log(f"write_command: 0x{cmd:02X}")
        GPIO.output(LCD_DC, GPIO.LOW)
        GPIO.output(LCD_SCE, GPIO.LOW)
        self.spi.writebytes([cmd])
        GPIO.output(LCD_SCE, GPIO.HIGH)
        
    def write_data(self, data):
        log(f"write_data: {list(data)[:10]}...")
        GPIO.output(LCD_DC, GPIO.HIGH)
        GPIO.output(LCD_SCE, GPIO.LOW)
        self.spi.writebytes(list(data))
        GPIO.output(LCD_SCE, GPIO.HIGH)
        
    def set_cursor(self, x, y):
        self.write_command(0x80 | x)
        self.write_command(0x40 | y)
        
    def clear(self):
        self.set_cursor(0, 0)
        self.write_data([0x00] * (LCD_WIDTH * LCD_HEIGHT // 8))
        
    def text(self, text, x=0, y=0):
        self.set_cursor(x, y)
        for char in text.upper():
            char_data = FONT_5X7.get(char, FONT_5X7[' '])
            self.write_data(char_data)
    
    def test_pattern(self):
        for i in range(84 * 48 // 8):
            self.write_data([0xFF])


class Keypad4x4:
    def __init__(self):
        self.callbacks = []
        
    def init(self):
        log("Initializing keypad...")
        for pin in KEYPAD_ROW_PINS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        for pin in KEYPAD_COL_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        log("Keypad initialized")
        
    def scan(self):
        for row_idx, row_pin in enumerate(KEYPAD_ROW_PINS):
            GPIO.output(row_pin, GPIO.LOW)
            time.sleep(0.005)
            
            for col_idx, col_pin in enumerate(KEYPAD_COL_PINS):
                if GPIO.input(col_pin) == GPIO.LOW:
                    key = KEY_MAP[row_idx][col_idx]
                    log(f"Key detected: {key}")
                    
                    time.sleep(0.1)
                    while GPIO.input(col_pin) == GPIO.LOW:
                        time.sleep(0.01)
                    
                    logger.info(f"Key pressed: {key}")
                    log(f"Keypad pressed: {key}")
                    print(f"Keypad pressed: {key}")
                    GPIO.output(row_pin, GPIO.HIGH)
                    time.sleep(0.05)
                    return key
            
            GPIO.output(row_pin, GPIO.HIGH)
        return None
    
    def get_key(self, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            key = self.scan()
            if key:
                for callback in self.callbacks:
                    callback(key)
                return key
            time.sleep(0.05)
        return None
    
    def register_callback(self, callback):
        self.callbacks.append(callback)


class HardwareInterface:
    def __init__(self):
        self.lcd = None
        self.keypad = None
        
    def init(self):
        log("Initializing hardware interface...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        log("GPIO mode set")
        
        self.lcd = Nokia5110LCD()
        log("LCD object created")
        self.lcd.init()
        log("LCD init done")
        
        self.keypad = Keypad4x4()
        log("Keypad object created")
        self.keypad.init()
        log("Keypad init done")
        
        log("Hardware Interface Ready!")
        
        return True
    
    def display_menu(self, categories, current_idx=0):
        self.lcd.clear()
        self.lcd.text("Order Now!", 0, 0)
        if current_idx < len(categories):
            self.lcd.text(categories[current_idx].get('name', ''), 0, 2)
        self.lcd.text("A:Sel B:Crt #Ord", 0, 5)
    
    def display_message(self, line1, line2=""):
        self.lcd.clear()
        self.lcd.text(line1, 0, 2)
        if line2:
            self.lcd.text(line2, 0, 4)
    
    def wait_for_input(self, prompt="Press key"):
        self.lcd.text(prompt, 0, 5)
        return self.keypad.get_key(timeout=30)
    
    def cleanup(self):
        GPIO.cleanup()


hw_interface = None

def get_hardware_interface():
    global hw_interface
    if hw_interface is None:
        hw_interface = HardwareInterface()
    return hw_interface


if __name__ == '__main__':
    log("Starting hardware test...")
    hw = get_hardware_interface()
    hw.init()
    
    log("Testing LCD...")
    hw.lcd.clear()
    hw.lcd.text("Test LCD", 0, 0)
    hw.lcd.text("Press keys", 0, 2)
    
    log("Starting keypad loop...")
    while True:
        key = hw.keypad.get_key(timeout=10)
        if key:
            log(f"Got key: {key}")
            hw.lcd.clear()
            hw.lcd.text(f"Key: {key}", 0, 2)