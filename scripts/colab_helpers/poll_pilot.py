"""Poll the pilot log from a Colab session.

Usage:  cat poll_pilot.py | colab exec
        cat poll_pilot.py | colab exec   # again later
"""
import os

LOG = "/content/pilot.log"

if not os.path.exists(LOG):
    print("No log yet — pilot not launched, or session is fresh.")
else:
    text = open(LOG).read()
    print(f"--- pilot.log ({len(text)} chars) ---")
    print(text[-4000:] if len(text) > 4000 else text)
