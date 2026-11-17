# Orbital Ambulance Technical Report

## Project scope

Orbital Ambulance adapts topic 14, Mini Hospital Supply Robot, into a Python game. A simulated ambulance carries supplies through an orbital station to one of two wards. The assessed methods are breadth first search (BFS), Bayesian inference, and a two state Markov decision process (MDP). A hidden Markov model (HMM) exercise extends the course material. The game uses no patient records or trained model.

The assessed demonstration uses one 5 by 5 floor, two wards, one noisy sensor report, two corridor states, and two actions. Larger maps and 30 levels are optional game extensions. The deterministic `demo.py` prints each method's input, calculation, result, and interpretation. The desktop game and Colab notebook use the same Python algorithm functions.

## System design

The ambulance starts at S and the player selects Ward A or B. The floor generator places walls and checks that both wards remain reachable. The menu offers 5, 10, 20, 40, 60, 100, or a fresh random map size each level. The campaign has 30 levels. A theme is drawn from 158 generated muted palettes. A challenge asks the player to calculate an algorithm result, then advances the ambulance one tile after a correct answer. Arrow keys or buttons control the ambulance between challenges. Five signal interference tabs must be closed on level 1; each later level adds one. The optional BFS hint starts hidden and costs half the level's starting energy each time it is activated.

The game state records the floor, target ward, position, energy, route, sensor history, challenge, and current interface mode. The interface is a Tkinter application with no external package requirement. The notebook uses ipywidgets in Colab and includes the same calculations. The soundtrack is a bundled WAV file; the desktop game plays it when enabled, while the notebook exposes browser audio controls.

## BFS route planning

**Input.** A 5 by 5 grid with start `(0, 2)`, Ward A `(4, 0)`, Ward B `(4, 4)`, and walls `(1, 0)`, `(1, 1)`, `(3, 1)`, `(1, 3)`, `(3, 3)`.

**Steps.** BFS puts the start in a FIFO queue. It visits valid neighbors, records each cell's predecessor, and stops when it removes the target from the queue. It then follows predecessors back to the start. In the fixed demonstration it expands 19 cells.

**Output.** The shortest route to Ward A is `(0,2), (1,2), (2,2), (3,2), (4,2), (4,1), (4,0)`. It has seven cells and six moves. Because every move has equal cost, BFS discovers the shortest path in move count.

## Bayesian hallway estimate

**Input.** The two states are FREE and BLOCKED. Assume `P(FREE)=0.82`, `P(CLEAR|FREE)=0.94`, and `P(CLEAR|BLOCKED)=0.12`. The observed report is ALERT. Thus `P(ALERT|FREE)=0.06` and `P(ALERT|BLOCKED)=0.88`.

**Calculation.** `P(FREE|ALERT) = (0.82 × 0.06) / (0.82 × 0.06 + 0.18 × 0.88) = 0.0492 / 0.2076 = 0.2370`.

**Output.** The estimated probability of a free hallway is 23.7%. This is a simulated probability based on a single noisy report, not a prediction about a real hospital.

## MDP action choice

**Input.** The states are FREE and BLOCKED, and the actions are CONTINUE and PAUSE. The one step rewards are `R(Continue, Free)=+10`, `R(Continue, Blocked)=-20`, `R(Pause, Free)=-2`, and `R(Pause, Blocked)=+2`. The state probability comes from Bayes: `P(FREE)=0.2370` and `P(BLOCKED)=0.7630`.

**Calculation.** `Q(Continue)=0.2370(10)+0.7630(-20)=-12.89`. `Q(Pause)=0.2370(-2)+0.7630(2)=+1.05`. The method selects the larger one step expected reward.

**Output.** PAUSE. The player remains free to move, but moving against the advice uses extra game energy. This is the simplified two state, two action one step model permitted in the project guidelines, not a full policy iteration solver.

## Extra HMM exercise

The HMM has hidden states FREE and BLOCKED. Transition probabilities are `P(F→F)=0.80`, `P(F→B)=0.20`, `P(B→F)=0.30`, `P(B→B)=0.70`. Sensor emissions use the same CLEAR likelihoods as Bayes. With reports CLEAR, ALERT, CLEAR and prior `P(FREE)=0.82`, Viterbi returns FREE, BLOCKED, FREE. The final path scores are approximately 0.0383 for FREE and 0.0114 for BLOCKED. HMM is additional; the assessed topic requires BFS, Bayes, and MDP.

## Testing and observed results

Run `python -m unittest discover -p "test_*.py" -v` and `python demo.py` from the repository root. Four automated tests passed locally. They check BFS shortest path and adjacency, Bayes numerical results, HMM sequence, MDP action selection, reachable generated floors at sizes 5, 20, and 100, difficulty changes, nonrepeating random sizes, and 158 palette accents. A desktop interaction smoke check also passed: it started a campaign, answered BFS, closed five tabs, paused and resumed, verified the hint energy cost, and verified that level 2 creates six tabs. A Colab interaction smoke check passed the four challenges and advanced to level 2. These are local results, not a claim that every combination of all 30 levels was manually played.

The fixed demonstration prints a six move BFS route, `P(FREE|ALERT)=23.7%`, `Q(Continue)=-12.89`, `Q(Pause)=+1.05`, and PAUSE. The route, hallway probability, and decision match the topic's expected outputs.

## Limits and assumptions

All maps, sensor reports, transition probabilities, and rewards are simulated teaching inputs. The game does not store or process patient data. The 100 by 100 option has a camera that follows the ambulance, so only part of the grid is visible at one time. The optional signal tabs and energy cost make the game harder, but they do not change the three algorithm definitions. The Colab version uses button controls because notebook keyboard focus varies by browser. The desktop version needs Python 3 and Windows for its bundled music playback path; the core algorithms run on other systems.

## Live demonstration plan

Open the desktop game, select 5 by 5, and press Ready. Explain the shortest path shown during the BFS question, answer it, then close the five interference tabs. Move the ambulance, show the Bayes posterior after a sensor report, and explain the MDP reward comparison at the ward. Run `python demo.py` if a fixed numerical example is needed. The presentation includes a short question and answer section for individual defense.
