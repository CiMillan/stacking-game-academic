import json, sys

# Calibrate p_i(s) = alpha * s^2 s.t. p'(s_dagger) = target_lambda
# Here target_lambda is a fraction of baseline reward R (set to 1.0 scale).
def calibrate(alpha0, HHI, s_dagger, frac_of_R=0.2, gamma=1.0):
    # alpha scales with HHI^gamma (policy choice)
    alpha = alpha0 * (HHI ** gamma)
    # Marginal penalty p'(s) = 2*alpha*s
    # Solve for alpha to hit chosen fraction at s_dagger
    if s_dagger <= 0:
        return {"alpha": alpha, "note":"s_dagger<=0; returning base alpha"}
    alpha_needed = (frac_of_R) / (2*s_dagger)
    # Combine base scaling with needed level
    # Choice: geometric mean to respect both; swap for your preference
    alpha_final = (alpha * alpha_needed) ** 0.5
    return {"alpha_base":alpha, "alpha_needed":alpha_needed, "alpha_final":alpha_final}

if __name__=="__main__":
    # argv: HHI s_dagger frac_of_R alpha0 gamma
    if len(sys.argv)<3:
        print("Usage: python -m src.data.calibrate_penalty <HHI> <s_dagger> [frac_of_R=0.2] [alpha0=1.0] [gamma=1.0]")
        sys.exit(2)
    HHI = float(sys.argv[1]); s_dagger=float(sys.argv[2])
    frac = float(sys.argv[3]) if len(sys.argv)>3 else 0.2
    alpha0 = float(sys.argv[4]) if len(sys.argv)>4 else 1.0
    gamma = float(sys.argv[5]) if len(sys.argv)>5 else 1.0
    print(json.dumps(calibrate(alpha0, HHI, s_dagger, frac, gamma), indent=2))
