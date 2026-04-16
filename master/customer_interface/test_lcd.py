# test_lcd.py - Test Nokia 5110 LCD
import sys
sys.path.insert(0, '.')
from hardware_interface import get_hardware_interface

hw = get_hardware_interface()
if hw.init():
    print("Hardware initialized!")
    hw.lcd.clear()
    hw.lcd.text("Nokia 5110 Test", 0, 0)
    hw.lcd.text("Welcome!", 0, 2)
    hw.lcd.text("Smart Restaurant", 0, 4)
    print("Display updated!")
else:
    print("Hardware init failed")