"""Allows to cross-check the relations between observer, cape and targets in each testbed
"""
from pathlib import Path

from shepherd_core import logger
from shepherd_core.data_models.testbed import Target
from shepherd_core.data_models.testbed import Testbed
from shepherd_core.testbed_client.fixtures import Fixtures

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    separator = "; "  # excel parses this as table, but not ","?!?
    path_csv = path_here / "content/testbed_layout.csv"
    with path_csv.open("w") as csv:
        elements = [
            "tb_id",
            "tb_name",
            "target_id",
            "target_name",
            "cape_id",
            "cape_name",
            "observer_id",
            "observer_name",
            "room",
            "lat",
            "long",
        ]
        string = separator.join(elements)
        csv.write(string + "\n")

        for fix_tb in Fixtures()["Testbed"]:
            tb = Testbed(id=fix_tb["id"])

            for fix_tgt in Fixtures()["Target"]:
                target = Target(id=fix_tgt["id"])

                try:
                    observer = tb.get_observer(target.id)
                except ValueError:
                    continue

                cape = observer.cape

                elements = [
                    str(tb.id),
                    tb.name,
                    str(target.id),
                    target.name,
                    str(cape.id),
                    cape.name,
                    str(observer.id),
                    observer.name,
                    observer.room,
                    str(observer.latitude),
                    str(observer.longitude),
                ]
                string = separator.join(elements)
                csv.write(string + "\n")
    logger.info("Wrote: %s", path_csv.as_posix())
