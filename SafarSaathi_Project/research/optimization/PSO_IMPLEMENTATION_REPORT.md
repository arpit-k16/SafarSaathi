# Particle swarm implementation

The same module implements bounded PSO: inertia 0.65, cognitive/social coefficients 1.4, velocity clamp ±0.25 in share space, seeded random coefficients, personal/global best updates and capped-simplex repair. Every position is evaluated using the same declared objective and capacities as GA. Best-so-far objective traces and candidate plans are retained.

Three seeds/three objective weights and parameter-budget sensitivity are compared with the identical baseline and an independent numerical convex reference. No globally optimal or operational recommendation is asserted. Stochastic convergence is not predictive calibration, hazard skill or a confidence percentage.
