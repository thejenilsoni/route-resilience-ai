# Demonstration data

The repository does not redistribute restricted or large satellite datasets. Instead, `scripts/generate_demo_data.py` creates a deterministic 48-node, 91-link urban network and `render_satellite_scene` renders a satellite-like RGB scene with road truth plus cloud, canopy and building-shadow masks.

The demonstration dataset exists to validate the software workflow. It must not be represented as an observed map of Delhi or as field-calibrated mobility data.

For production use, preserve source, acquisition time, licence, projection, ground sampling distance, cloud mask, preprocessing version and quality flags for every raster/vector asset.
