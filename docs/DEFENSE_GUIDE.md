# Project Defense Guide

## Problem and objectives, about 2 minutes

The project simulates a supply ambulance moving to one of two wards on a small station map. Its three assessed objectives are to find a shortest route, update the probability that a hallway is free after one sensor report, and choose between continuing and pausing under uncertainty. The fixed demonstration uses a 5 by 5 grid and no patient data. The game adds 30 levels and an optional HMM exercise for interaction.

## Live demo, about 3 to 5 minutes

1. Start the desktop game with `START_GAME.bat`, select 5 by 5, then press Ready.
2. Count the BFS route moves on the temporary highlighted path and answer the question.
3. Close all five signal tabs. Show that the ambulance is controlled with W, A, S, D or arrows. Mention that Hint costs half the starting energy.
4. Scan a corridor or move to trigger a report. Explain that the displayed probability changes with CLEAR or ALERT.
5. Reach the final step and compare the two MDP expected rewards. If time is short, run `python demo.py` for a deterministic example.

## Three AI methods, about 2 minutes

**BFS:** A FIFO queue visits reachable cells in layers. The first path to the ward has the fewest moves.

**Bayes:** Multiply the prior for each state by the likelihood of the observed report, then divide the FREE term by the sum of both terms. An ALERT changes the fixed example's free probability from 82% to 23.7%.

**MDP:** Use the posterior as the two state belief. Continue has expected reward -12.89, while Pause has +1.05, so the one step model recommends Pause.

## Questions to practise, up to 3 minutes

- Why is BFS shortest? All grid moves cost one, and the FIFO queue expands cells by distance.
- Is the sensor always correct? No. Its sensitivity and false alarm rate are explicit assumptions.
- Why does an ALERT still leave a 23.7% free chance? Bayes combines the uncertain report with the prior.
- Is this a full MDP solver? No. The assignment permits one step expected reward for two states and two actions.
- Why include HMM? It demonstrates how three sequential reports can infer a hidden state path; it is an optional extension.
- Does the project use patient records or a trained model? No. All inputs are simulated.
