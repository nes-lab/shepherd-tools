from pathlib import Path

names_elf = ["build_msp.elf", "build_nrf.elf"]

files_elf = [Path(__file__).resolve().with_name(name) for name in names_elf]
