import numpy as np
from theawase import config
from theawase.entities.fish import FishAI, FishState, BiteType
from theawase.physics.bait import BaitModel

def verify_atari_physics():
    print("=== Atari Physics Verification ===")
    
    # 1. Setup
    fish = FishAI(position=np.array([0.0, -0.5]))
    bait = BaitModel()
    bait.position = np.array([0.0, -0.5]) # Bait at same pos
    
    # SUCK_TO_FLOAT_FACTOR matches main.py
    SUCK_TO_FLOAT_FACTOR = 0.02
    
    # 2. Test KUIAGE (Lift)
    print("\n[Test Case: KUIAGE]")
    fish.state = FishState.ATTACK
    fish.bite_type = BiteType.KUIAGE
    fish.position = np.array([0.0, -0.5]) # Reset pos
    fish.suck_strength = 5.0 # Max strength
    
    # Fish moves UP relative to bait for KUIAGE? 
    # Actually logic says fish moves UP, and bait is AT fish position roughly.
    # If fish is ABOVE bait, vector r = bait - fish points DOWN.
    # force_dir = -r/dist points UP.
    # So if fish is slightly ABOVE bait, it pulls bait UP.
    
    # Let's simulate: Fish is exactly at bait.
    # If exactly at bait, force is 0.
    # Fish moves UP (velocity +y).
    fish.velocity = np.array([0.0, 0.2]) 
    # Advance time small bit so fish moves up
    fish.position += fish.velocity * 0.1 
    
    suck_force = fish.get_suck_force(bait.position)
    suck_on_float = suck_force * SUCK_TO_FLOAT_FACTOR
    
    print(f"Fish Pos: {fish.position}")
    print(f"Bait Pos: {bait.position}")
    print(f"Suck Force on Float: {suck_on_float}")
    
    if suck_on_float[1] > 0:
        print(">> OK: Force is UPWARD (Float rises)")
    else:
        print(">> FAIL: Force is not upward")

    # 3. Test KESHIKOMI (Plunge)
    print("\n[Test Case: KESHIKOMI]")
    fish.state = FishState.ATTACK
    fish.bite_type = BiteType.KESHIKOMI
    fish.position = np.array([0.0, -0.5])
    fish.suck_strength = 5.0
    
    # Fish moves DOWN
    fish.velocity = np.array([0.0, -0.2])
    fish.position += fish.velocity * 0.1
    
    suck_force = fish.get_suck_force(bait.position)
    suck_on_float = suck_force * SUCK_TO_FLOAT_FACTOR
    
    print(f"Fish Pos: {fish.position}")
    print(f"Bait Pos: {bait.position}")
    print(f"Suck Force on Float: {suck_on_float}")
    
    if suck_on_float[1] < 0:
        print(">> OK: Force is DOWNWARD (Float plunges)")
    else:
        print(">> FAIL: Force is not downward")

    # 4. Sawari Check
    print("\n[Test Case: SAWARI]")
    fish.state = FishState.APPROACH
    fish.position = np.array([0.1, -0.5]) # Close to bait
    fish._approach_behavior(0.016, bait.position, 1.0) # Trigger update
    dist_force = fish.get_disturbance_force()
    print(f"Disturbance Force: {dist_force}")
    if np.linalg.norm(dist_force) > 0:
         print(">> OK: Disturbance force generated")
    else:
         print(">> FAIL: No disturbance")

if __name__ == "__main__":
    verify_atari_physics()
