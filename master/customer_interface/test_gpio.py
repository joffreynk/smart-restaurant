#!/usr/bin/env python3
"""
Test if keypad works with pull-up (for keypads without built-in resistors)
"""
import RPi.GPIO as GPIO
import time

print("Testing GPIO pins with PULL-UP...")
print("Make sure you have external pull-down resistors (10kΩ) on columns!")
print("=" * 50)

row_pins = [19, 26, 20, 21]
col_pins = [16, 12, 25, 24]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("\n[1] Setting row pins as OUTPUT...")
for pin in row_pins:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

print("\n[2] Setting column pins as INPUT with PULL DOWN...")
print("NOTE: If no external resistors, try PULL_UP instead\n")
for pin in col_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Testing 5 cycles... Press keys now!\n")

for cycle in range(5):
    print(f"Cycle {cycle+1}:")
    for row_idx, row_pin in enumerate(row_pins):
        GPIO.output(row_pin, GPIO.HIGH)
        time.sleep(0.05)
        
        for col_idx, col_pin in enumerate(col_pins):
            if GPIO.input(col_pin) == GPIO.HIGH:
                print(f"  *** PRESSED: Row {row_idx+1}, Col {col_idx+1} ***")
        
        GPIO.output(row_pin, GPIO.LOW)
        time.sleep(0.1)

print("\nTest complete!")
GPIO.cleanup()
