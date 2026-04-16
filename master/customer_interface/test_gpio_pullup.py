#!/usr/bin/env python3
"""
Alternative test - try with PULL UP (for keypads with pull-up resistors built-in)
"""
import RPi.GPIO as GPIO
import time

print("Testing with PULL UP...")
print("=" * 50)

row_pins = [19, 26, 20, 21]
col_pins = [16, 12, 25, 24]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in row_pins:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)

for pin in col_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Testing... Press any key!\n")

for cycle in range(3):
    for row_idx, row_pin in enumerate(row_pins):
        GPIO.output(row_pin, GPIO.LOW)
        time.sleep(0.05)
        
        for col_idx, col_pin in enumerate(col_pins):
            if GPIO.input(col_pin) == GPIO.LOW:
                print(f"  *** PRESSED: Row {row_idx+1}, Col {col_idx+1} ***")
        
        GPIO.output(row_pin, GPIO.HIGH)
        time.sleep(0.1)

print("\nDone!")
GPIO.cleanup()
