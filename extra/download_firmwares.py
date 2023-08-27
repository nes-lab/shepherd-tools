"""
script will:
- download and extract firmware-models from https://github.com/orgua/shepherd-targets/releases
"""
from urllib.request import urlopen
from zipfile import ZipFile
from pathlib import Path
from io import BytesIO

if __name__ == "__main__":

    link = "https://github.com/orgua/shepherd-targets/releases/latest/download/firmwares.zip"
    # ⤷ already includes embedded-firmware-models

    data = urlopen(link).read()
    path_here = Path(__file__).parent.absolute()

    with ZipFile(BytesIO(data), 'r') as zip_ref:
        zip_ref.extractall(path_here)

