"""Reproducible 5x5 demonstration for Mini Hospital Supply Robot, topic 14."""

from medbot_x import bayes_free, bfs_trace, mdp_decision, viterbi


def main():
    size = 5
    start = (0, 2)
    wards = {"A": (4, 0), "B": (4, 4)}
    walls = {(1, 0), (1, 1), (3, 1), (1, 3), (3, 3)}
    route, expanded = bfs_trace(start, wards["A"], size, walls)
    report = "ALERT"
    prior, sensitivity, false_alarm = 0.82, 0.94, 0.12
    posterior, free_term, blocked_term = bayes_free(
        report, prior, sensitivity, false_alarm
    )
    action, values = mdp_decision(posterior)
    observations = ("CLEAR", "ALERT", "CLEAR")
    hidden_path, _ = viterbi(observations, prior, sensitivity, false_alarm)

    print("SCENARIO: 5x5 station, two wards, no patient data")
    print(f"BFS input: start={start}, Ward A={wards['A']}, walls={sorted(walls)}")
    print(f"BFS steps: expanded {expanded} cells; route contains {len(route)} cells")
    print(f"BFS output: {route} ({len(route) - 1} moves)")
    print("BFS meaning: the ambulance can use this shortest route to Ward A.")
    print(f"BAYES input: {report}, P(free)={prior:.2f}, sensitivity={sensitivity:.2f}, false alarm={false_alarm:.2f}")
    print(f"BAYES steps: {free_term:.4f} / ({free_term:.4f} + {blocked_term:.4f})")
    print(f"BAYES output: P(free | {report})={posterior:.4f} ({posterior:.1%})")
    print("BAYES meaning: an alert lowers confidence that the hallway is free.")
    print(f"MDP input: two states FREE/BLOCKED, actions CONTINUE/PAUSE, P(free)={posterior:.4f}")
    print(f"MDP steps: Q(Continue)={values['CONTINUE']:+.2f}; Q(Pause)={values['PAUSE']:+.2f}")
    print(f"MDP output: {action}")
    print("MDP meaning: pausing has the higher expected one-step reward here.")
    print(f"EXTRA HMM input: {observations}; Viterbi path={hidden_path}")


if __name__ == "__main__":
    main()
