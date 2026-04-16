#!/usr/bin/env python3
"""
LCD test using hardware_interface
"""
import sys
sys.path.insert(0, '.')
from hardware_interface import get_hardware_interface

print("Testing LCD and Keypad...")
print("=" * 50)

hw = get_hardware_interface()
hw.init()

print("\nLCD test - filling screen...")
hw.lcd.test_pattern()

print("\nKeypad test - press any key (5 second timeout)...")
key = hw.keypad.get_key(timeout=5)
if key:
    print(f"KEY PRESSED: {key}")
else:
    print("No key pressed (timeout)")

print("\nTest complete!")
