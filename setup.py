from pathlib import Path
from setuptools import setup

# The text of the README file
README = (Path(__file__).parent / "README.md").read_text()

requirements = [
    "click",
    "h5py",
    "matplotlib",
    "numpy",
    "pandas",
    "pyYAML",
    "scipy",
    "tqdm",
    "samplerate",
]

setup(
    name="shepherd_data",
    version="0.6.0",
    description="Programming- and CLI-Interface for the h5-dataformat of the Shepherd-Testbed",
    long_description=README,
    long_description_content_type="text/markdown",
    packages=["shepherd_data"],
    license="MIT",
    classifiers=[
        # How mature is this project? Common values are
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3",
    ],
    install_requires=requirements,
    author="Ingmar Splitt",
    author_email="ingmar dot splitt at tu-dresden dot de",
    entry_points={"console_scripts": ["shepherd-data=shepherd_data.cli:cli"]},
)
