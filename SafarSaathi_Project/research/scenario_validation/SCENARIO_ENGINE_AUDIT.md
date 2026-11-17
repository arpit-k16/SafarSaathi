# Scenario engine audit

The existing capacity_scenario function is one-period conservation accounting. It has four explicit inputs: baseline visitor equivalents, visitor-place capacity, demand change percent and available-capacity percent. It has no rainfall, runoff, hydrodynamics, terrain, routing, accommodation observation or emergency-dispatch model. Original UI controls for those concepts are labeled unmodeled context.

Demand = B(1+d/100); available capacity = C a/100; served = min(demand, available capacity); unserved = max(0, demand−capacity). Utilization is demand/capacity, null at zero capacity. Baseline uses B, C with no changes. All inputs are hypothetical, not inferred local conditions. Output has no affected locations.

Rainfall/accessibility/resource fields are explicitly rejected rather than assigned arbitrary causal coefficients. Reduced accommodation can be represented only as an explicitly assumed reduction in visitor-place capacity; reduced road access can be a hypothetical aggregate capacity loss, not a validated road-state calculation. Emergency resource limits are supported separately as explicit bottleneck capacities in the optimizer, not as a learned scenario relation.

Hardening preserves the formula: huge integers now yield input errors instead of overflow; an unrepresentable utilization ratio is rejected rather than emitted as Infinity/invalid JSON. No predictive flood accuracy is claimed.
