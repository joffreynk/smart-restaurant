#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from hardware_interface import get_hardware_interface

print("Testing LCD...")
hw = get_hardware_interface()
hw.init()

print("Testing keypad...")
key = hw.keypad.get_key(timeout=10)
print(f"Key pressed: {key}")
