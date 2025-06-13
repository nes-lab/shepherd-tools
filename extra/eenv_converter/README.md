# Converter for Energy Environments

## Bonito

Paper: <https://nes-lab.org/pubs/2022-Geissdoerfer-Bonito.pdf>

Main Repo: <https://github.com/geissdoerfer/bonito>

Zenodo Data: <https://zenodo.org/records/6383042>

---

Multiple datasets recorded with shepherd v1 where presented in the bonito-paper and published via zenodo.
As the zenodo-data is processed to only include power-traces, we use the original raw data.

To convert, simply copy the scripts into your source directory, with the raw-files located in `neslab-eh-data`. Run `python3 convert_bonito_eenvs.py` and the content directory will be filled.

## Flocklab / Rocketlogger

Zenodo Data: <https://zenodo.org/records/3715472>

**WORK IN PROGRESS**

A long-term dataset was published and could be made accessible for the Shepherd Testbed.

The data contains recordings of 6 nodes for several month.
The sampling rate is rather low, but it includes traces of a light sensor.
These traces could be:

- upsampled
- reviewed and cut down to include scenarios like: night, sun set, sun rise, morning, ...
