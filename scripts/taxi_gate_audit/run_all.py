"""Run the whole Taxi-Gate audit pipeline (read-only on every source)."""
import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STEPS = ['s01_forensics', 's02_coa', 's03_matching', 's04_integration', 's05_qa', 's06_build', 's07_postbuild']

if __name__ == '__main__':
    for s in STEPS:
        t = time.time()
        importlib.import_module(s).main()
        print(f'[{s}] {time.time() - t:.0f}s', flush=True)
