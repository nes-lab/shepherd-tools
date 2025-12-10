# Shepherd - Tools

`Legacy_bugfix`-branch!
This exists as long as the testbed does not include the Battery-model.

```bash
~/local/bin/uv pip install git+https://github.com/nes-lab/shepherd-tools.git@legacy_bugfix#subdirectory=shepherd_core -U

scp -o StrictHostKeyChecking=no jane@192.168.165.201:/opt/shepherd/software/python-package/pyproject.toml jane@192.168.165.202:/opt/shepherd/software/python-package/pyproject.toml

sudo -E ~/.local/bin/uv pip install /opt/shepherd/software/python-package/.[test] --upgrade --system --break-system-packages

```
