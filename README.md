# Orbital Ambulance — Emergency Supply Run

A desktop game for AI Fundamentals topic 14, Mini Hospital Supply Robot. **You drive a space ambulance** through procedurally generated orbital station floors. The campaign has 30 levels; the next level starts automatically after you reach the target ward. No patient data is used.

## Start the game

1. Download the repository ZIP from GitHub or clone it.
2. Keep `START_GAME.bat`, `medbot_x.py`, and `medbot_theme.wav` in the same folder.
3. Double-click `START_GAME.bat`.

Python 3 is required. Alternatively, open a terminal in that folder and run `python medbot_x.py`. The game uses Tkinter from Python's standard library; no extra game package is needed.

For the Google Colab edition, open `MEDBOT-X_Hospital_Supply_Robot.ipynb` with Colaboratory and choose **Runtime → Run all**. The desktop game has the larger map view and vector characters.

## Controls

| Control | Action |
|---|---|
| Map size menu | Choose 5×5, 10×10, 20×20, 40×40, 60×60, 100×100, or Random |
| Ready · start mission | Begin level 1 of 30 with the route hint off |
| Arrow keys or W/A/S/D | Drive the ambulance one tile; on-screen direction buttons also work |
| E or Scan button | Scan the corridor in front of the robot |
| Space or Wait button | Wait one turn and allow a new sensor reading |
| H or Hint button | Reveal the BFS route; each activation costs half the level's starting Energy. Turning it off is free. |
| Signal Interference tabs | Click × on every tab before you can drive. Level 1 has five tabs; each later level adds one. |
| Pause or Esc | Pause or resume the game |
| Resume / Restart level / Main menu | Available in the pause menu |
| + / − | Zoom the map; large maps follow the robot |
| How to play | Open the tutorial from the main menu |
| Background music | Turn the looping soundtrack on or off in the main menu |

**You move the ambulance.** After it reaches the ward, the next level starts automatically. **Random** picks a new map size for every level and never repeats the same size immediately. Every level also changes the station layout and visual theme. The ambulance uses 158 generated visual variants in four map styles: Clinic, Pixel, Realistic-inspired and Mixed.

For the clearest first run, leave **Map size = 5** and click **Ready · start mission**. The ambulance starts at **S**. First solve the BFS route question. A correct answer reveals the calculation and moves the ambulance one step. Then close all incoming Signal Interference tabs. Drive toward **A** or **B**. The dotted BFS route is visible during its question, then hidden unless you pay Energy for Hint. Bayes and HMM challenges appear along the route, and an MDP challenge appears before the final step. Each correct answer moves the ambulance one step. **Between challenges, an arrow press moves one tile if the visible map cell is open.** Sensor warnings do not block movement; moving against MDP advice costs extra Energy. You can scan with **E** or wait with **Space** before deciding. Energy also decreases on scans and wall bumps. The visual palettes are dark and low saturation.

Difficulty rises over the campaign through a higher wall density, a lower prior chance of a free corridor and less reliable sensor reports. The map generator checks that both wards remain reachable. Each floor still has exactly two wards and two possible corridor states.

## Four working AI methods

Each method has a separate interactive challenge. The sidebar shows the live inputs; after you answer correctly, the game shows the calculation and advances the robot one step.

| Method | Task | Calculation shown |
|---|---|---|
| BFS | Find a shortest route through the generated floor | Number of expanded cells and route length |
| Bayes' theorem | Estimate a free hallway from one noisy sensor report | Numerator, denominator and posterior probability |
| HMM / Viterbi | Infer hidden corridor states from the latest three reports | Most likely state sequence and final state scores |
| MDP | Advise whether to Continue or Pause | One-step expected reward for both actions; the player decides |

The course's topic 14 requires **BFS, Bayes and MDP**. HMM is an extra demonstration. The 2-state MDP uses the one-step expected reward variant allowed by the project guidelines. Sensor probabilities, HMM transitions and rewards are simulated teaching assumptions; there is no trained model or real medical dataset. Run `python demo.py` for a reproducible 5×5 example that prints input, calculation, output and interpretation for each method.

## Example

With a Level 1 prior of 82%, sensor sensitivity of 94%, and false alarm rate of 12%, a CLEAR report gives:

```text
P(free | CLEAR) = (0.82 × 0.94) / (0.82 × 0.94 + 0.18 × 0.12) ≈ 97.3%
```

BFS computes a route from your current tile. HMM starts reporting after the third sensor observation. MDP uses the Bayes result on each scan to compare Continue and Pause; its advice does not override your controls.

### Fixed 5×5 demonstration output

`python demo.py` uses Ward A at `(4, 0)` and an `ALERT` sensor report. Its BFS route has **6 moves**. Bayes computes `P(free | ALERT) = 0.0492 / (0.0492 + 0.1584) = 23.7%`. The MDP compares `Q(Continue) = -12.89` with `Q(Pause) = +1.05` and recommends **PAUSE**. See [technical report](docs/TECHNICAL_REPORT.md) for the inputs and steps.

## Submission material

- [Technical report](docs/Orbital_Ambulance_Technical_Report.pdf) ([editable text](docs/TECHNICAL_REPORT.md))
- [Team contribution statement](docs/Orbital_Ambulance_Team_Contributions.pdf) ([editable text](docs/TEAM_CONTRIBUTIONS.md); proposed roles to confirm with the team)
- [Defense guide](docs/DEFENSE_GUIDE.md)
- [Presentation](docs/Orbital_Ambulance_Presentation.pptx)

The AI usage declaration and demo video are intentionally not included in this version.

## Tests

From the extracted folder:

```powershell
python -m unittest discover -p "test_*.py" -v
```

The code and project material were prepared with AI assistance. The assumptions and intermediate calculations are visible in the game and in the source code.
