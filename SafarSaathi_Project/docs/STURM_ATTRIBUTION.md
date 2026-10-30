# STURM-Flood experiment attribution

Source: Notarangelo, Nicla; WEO SAS. STURM-Flood (2024-07-16).
DOI: https://doi.org/10.5281/zenodo.12748983
Dataset record: https://zenodo.org/records/12748983
Dataset license: Creative Commons Attribution 4.0 International,
https://creativecommons.org/licenses/by/4.0/

Changes: selected delivered Sentinel-1 tiles whose reference/image acquisition
times differ by no more than 24 hours; reference masks binarized using the
publisher-documented >0 convention; local-neighborhood features extracted for
a CPU baseline. No endorsement by the dataset creators is implied. The archive
and example source tile are excluded from the distributed ZIP. Held-out mask
and prediction thumbnails are included as attributed evaluation illustrations.

The publisher code repository uses separate terms. Its code and weights are
not copied into this project. Our target follows its published convention,
https://github.com/STURM-WEO/STURM-Flood/blob/main/utils/utility.py.

The resulting model identifies reference-positive water/flood extent, without
independently distinguishing permanent water or estimating calibrated flood
probability. Its bounded country/event benchmark does not establish performance
in Uttarakhand. See model metadata for exact sample identities and metrics.
