# Orbital Ambulance

Orbital Ambulance is a small Python game based on **AI Fundamentals topic 14: Mini Hospital Supply Robot**. You drive a space ambulance carrying supplies through an orbital station to one of two wards. The station floor has walls, uncertain corridor conditions, and noisy sensor reports. The game uses simulated data only and contains no patient information.

The assessed demonstration is deliberately small: a **5×5 grid, two wards, two corridor states, and two possible actions**. The full game expands that idea into 30 levels with changing maps and visual themes. You steer the ambulance with the arrow keys or W/A/S/D. A correct answer to an AI challenge moves it one step; between challenges, you drive it yourself. Signal interference appears as tabs that must be closed before driving. The optional route hint costs energy.

## How AI works in the game

| Method | Question the game asks | Result |
|---|---|---|
| BFS | What is the shortest route from the ambulance to the ward? | A path and its number of moves |
| Bayes' theorem | How likely is a hallway to be free after one CLEAR or ALERT report? | An updated probability |
| MDP | Is Continue or Pause better under the current uncertainty? | The action with the higher one-step expected reward |
| HMM / Viterbi | What hidden corridor states best explain three sensor reports? | A most likely state sequence (extra exercise) |

BFS, Bayes, and MDP are the three methods required for topic 14. HMM is an additional lesson. The game shows the inputs and calculations so each decision can be explained during the project defense. Run python demo.py from the repository root for one reproducible 5×5 example: a six-move route, a 23.7% free-hallway probability after ALERT, and a PAUSE recommendation.

## Project files

- [Technical report](Orbital_Ambulance_Technical_Report.pdf) explains the assumptions, algorithms, worked example, tests, and limitations.
- [Seven-slide presentation](Orbital_Ambulance_Presentation.pptx) covers the live defense.
- [Defense guide](DEFENSE_GUIDE.md) provides a demo sequence and likely questions.
- [Team contribution statement](Orbital_Ambulance_Team_Contributions.pdf) contains proposed roles for the four members to confirm.

To play, return to the [repository home page](..) and follow the start instructions in the main README.
