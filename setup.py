"""
install with 'python setup.py install'
"""
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
    "samplerate",  # TODO: test for now
]

setup(
    name="shepherd_data",
    version="2022.5.2",  # year.month.sub
    description="Programming- and CLI-Interface for the h5-dataformat of the Shepherd-Testbed",
    long_description=README,
    long_description_content_type="text/markdown",
    packages=["shepherd_data"],
    license="MIT",
    license_file="LICENSE",
    classifiers=[
        # How mature is this project? Common values are
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    url="https://github.com/orgua/shepherd-datalib",
    project_urls={
        "Bug Tracker": "https://github.com/orgua/shepherd-datalib/issues",
    },
    install_requires=requirements,
    author="Ingmar Splitt, Kai Geissdoerfer",
    entry_points={"console_scripts": ["shepherd-data=shepherd_data.cli:cli"]},
    python_requires=">=3.6",
)
