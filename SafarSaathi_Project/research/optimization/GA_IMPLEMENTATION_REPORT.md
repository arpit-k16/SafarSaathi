# Genetic algorithm implementation

src/safarsaathi_ml/optimization.py implements a real-valued GA: seeded population containing the proportional baseline, tournament selection of three candidates, per-gene blend crossover, 25% Gaussian mutation (standard deviation 0.10 in share space), capped-simplex repair and elite preservation. Evaluations call the declared objective, not random score updates. Best-so-far convergence is recorded every generation.

Experiments use three seeds and three exposure/utilization weightings; parameter sensitivity changes population/iteration budgets. Runtime is measured wall-clock and not deterministic. Candidate vectors and objective traces are reproducible for fixed software/input/seed. Objective improvements are numerical proxy improvements on the labeled hypothetical fixture, not empirical intervention effectiveness.
