#!/usr/bin/env python3
"""
Fix Color Sensor Script
Updates all files to use correct frequency scaling
"""

import os
from pathlib import Path

print("=" * 70)
print(" FIXING COLOR SENSOR FREQUENCY SCALING")
print("=" * 70)

# Files to update
files_to_update = [
    'test_color_sensor.py',
    'calibrate_color_sensor.py',
    'collect_training_data.py',
    'coffee_sorter_simple.py',
    'coffee_sorter_ml.py',
    'diagnose_readings.py'
]

# Old code (20% frequency)
old_code = """GPIO.output(config.COLOR_S0, GPIO.HIGH)
GPIO.output(config.COLOR_S1, GPIO.LOW)"""

# New code (2% frequency) - MUCH BETTER FOR RASPBERRY PI
new_code = """GPIO.output(config.COLOR_S0, GPIO.LOW)
GPIO.output(config.COLOR_S1, GPIO.HIGH)"""

print("\nThis will change frequency scaling from 20% to 2%")
print("This should reduce your RGB values by 10x to normal range")
print()

updated = 0
not_found = 0

for filename in files_to_update:
    filepath = Path(filename)
    
    if not filepath.exists():
        print(f"⚠️  {filename} - Not found (skipping)")
        not_found += 1
        continue
    
    # Read file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if it needs updating
    if old_code in content:
        # Replace
        new_content = content.replace(old_code, new_code)
        
        # Write back
        with open(filepath, 'w') as f:
            f.write(new_content)
        
        print(f"✓ {filename} - Updated")
        updated += 1
    else:
        print(f"○ {filename} - Already correct or different format")

print("\n" + "=" * 70)
print(f" SUMMARY")
print("=" * 70)
print(f"Files updated: {updated}")
print(f"Files not found: {not_found}")

if updated > 0:
    print("\n✓ Color sensor frequency changed to 2%")
    print("  Your RGB values should now be 10x lower (normal range)")
    print("\n📊 Next steps:")
    print("  1. Test with: python3 test_color_sensor.py")
    print("  2. Values should now be 400-1500 range")
    print("  3. Re-run calibration: python3 calibrate_color_sensor.py")
else:
    print("\n⚠️  No files were updated")
    print("  You may need to manually edit the files")

print("\n" + "=" * 70)
