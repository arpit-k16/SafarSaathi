# Historical case-study methodology

The deliverable is an evidence-readiness assessment and an executable inventory check. Event verification is complete within the cited scope; quantitative historical model validation is **not** complete.

## Analysis contract

- **Geography:** independently delineated Nepal/China source–pathway–receptor corridor, using genuine Nepal assets. Do not use the Uttarakhand SVG schematic, NASA grid/query points or Indian tourism counts as Nepal infrastructure/exposure.
- **Time:** distinguish acquisition time, observed phenomenon, label date, publication time and decision cutoff. Convert Nepal local times with explicit source/timezone metadata; do not assume differently located clock observations are the same flood-wave arrival time.
- **Target:** determine whether each original reference polygon represents standing/transient water, debris/mass-movement deposits, damaged assets, or another class. The existing STURM model predicts publisher reference-positive water/flood pixels and cannot automatically be scored against a debris-deposit map.
- **Evidence:** retain original metadata/license/vintage/hash for each acquisition and reference. Document cloud/no-data masks, resolution, geotransforms and any resampling. Work in derived directories only.

## Steps that require missing data

1. Obtain bounded, licensed pre-event, event-period and post-event imagery covering the actual corridor; verify scene IDs, dates, bands, calibration, CRS and bounds.
2. Obtain original authoritative reference vectors/raster labels and their class definitions. Validate geometry and temporal compatibility. A web illustration is not a ground-truth mask.
3. Obtain Nepal road/bridge, river, hospital and tourism-location layers plus dated access/closure observations. A mapped road is not an open or safe road.
4. Define independent event/spatial holdout before fitting thresholds or preprocessing; keep all tiles of this event out of training and tuning. Fit learned transformations on training data only.
5. Align compatible imagery/labels in an appropriate projected CRS for area/length, or use geodesic calculations where appropriate. Quantify no-data/cloud exclusions and valid evaluation area.
6. If target definitions align, compute confusion matrix, precision, recall, IoU and Dice on independent pixels/scenes; report uncertainty at event/scene level rather than treating correlated pixels as independent samples.
7. Intersect observed event extent with validated Nepal assets for **potential exposure**; compare dated damage/access observations separately. No exposure-to-casualty or route-safety inference without evidence.
8. Report disagreements, boundary uncertainty, missed/transient changes, pre-event information availability and domain shift. Do not tune on this same event and then report it as independent validation.

## Interpretive separation

**Historical reconstruction** uses post-event evidence and cannot establish advance prediction. **Hypothetical capacity accounting** conserves visitor demand/places under explicit inputs and does not model flood physics. **Disaster prediction** requires pre-cutoff features, appropriate event labels and independent out-of-time/out-of-region performance. Neither of the first two provides the third.

No physically based hydrodynamic model, calibrated cryosphere trigger model, historical publication-time replay or measured Nepal tourist panel is present. Their absence is a substantive limitation, not permission to manufacture scenario inputs.
