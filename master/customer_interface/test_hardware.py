"""
Test Nokia 5110 LCD (PCD8544) with 4x4 Keypad
Wiring for Raspberry Pi

=================== Nokia 5110 LCD ====================
| LCD Pin | Function    | Raspberry Pi | BCM GPIO |
|---------|-------------|--------------|----------|
| VCC     | 3.3V Power  | Pin 1        | -        |
| GND     | Ground      | Pin 6        | -        |
| SCE     | Chip Select | Pin 12       | GPIO 18  |
| RST     | Reset       | Pin 16       | GPIO 23  |
| D/C     | Data/Cmd    | Pin 18       | GPIO 24  |
| MOSI    | SPI MOSI    | Pin 19       | GPIO 10  |
| SCLK    | SPI Clock   | Pin 23       | GPIO 11  |
| LED     | Backlight   | Pin 33       | GPIO 13  |

=================== 4x4 Keypad ====================
| Row/Col | BCM GPIO | Physical Pin |
|---------|----------|--------------|
| R1      | GPIO 17  | Pin 11       |
| R2      | GPIO 27  | Pin 13       |
| R3      | GPIO 22  | Pin 15       |
| R4      | GPIO 5   | Pin 29       |
| C1      | GPIO 6   | Pin 31       |
| C2      | GPIO 21  | Pin 40       |
| C3      | GPIO 19  | Pin 35       |
| C4      | GPIO 26  | Pin 37       |

Key Map:
+--------+--------+--------+--------+
|   1    |   2    |   3    |   A    |
+--------+--------+--------+--------+
|   4    |   5    |   6    |   B    |
+--------+--------+--------+--------+
|   7    |   8    |   9    |   C    |
+--------+--------+--------+--------+
|   *    |   0    |   #    |   D    |
+--------+--------+--------+--------+
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_keypad():
    print("=" * 50)
    print("Testing 4x4 Keypad")
    print("=" * 50)
    
    try:
        from hardware_interface import get_hardware_interface
        
        hw = get_hardware_interface()
        if not hw.init():
            print("FAILED: Hardware init failed")
            return False
        
        print("SUCCESS: Keypad initialized")
        print("Press keys (5 second timeout)...")
        
        for i in range(10):
            key = hw.keypad.get_key(timeout=5)
            if key:
                print(f"Key pressed: {key}")
            else:
                print("Timeout, no key pressed")
                break
        
        hw.cleanup()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_nokia():
    print("=" * 50)
    print("Testing Nokia 5110 LCD")
    print("=" * 50)
    
    try:
        from hardware_interface import get_hardware_interface
        
        hw = get_hardware_interface()
        if not hw.init():
            print("FAILED: Hardware init failed")
            return False
        
        hw.lcd.clear()
        hw.lcd.text("Nokia 5110 Test", 0, 0)
        hw.lcd.text("Hello World!", 0, 2)
        hw.lcd.text("1234567890ABCD", 0, 4)
        
        print("SUCCESS: Nokia LCD test passed")
        hw.cleanup()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("\n" + "=" * 50)
    print("HARDWARE TEST SUITE")
    print("=" * 50 + "\n")
    
    results = []
    
    if len(sys.argv) > 1:
        test = sys.argv[1]
        if test == 'keypad':
            results.append(("Keypad", test_keypad()))
        elif test == 'nokia':
            results.append(("Nokia", test_nokia()))
    else:
        print("Running all tests...\n")
        
        print("[1] Test Keypad")
        results.append(("Keypad", test_keypad()))
        print()
        
        print("[2] Test Nokia 5110")
        results.append(("Nokia", test_nokia()))
    
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
