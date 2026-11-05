#!/usr/bin/env python3
"""Print the deterministic scripted scenario trace + digest. No network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_sim import scripted_scenario

if __name__ == "__main__":
    sim = scripted_scenario()
    print("\n".join(sim.trace))
    print(f"snapshot={sim.snapshot()}")
    print(f"observed_verdict={sim.observed_verdict('robot-a')}")
    print(f"trace_sha256={sim.trace_digest()}")
