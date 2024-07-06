import argparse
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple, Dict

logging.basicConfig(level=logging.INFO)

INFILE: str = "nodes.svg"
OUTDIR: str = "."

# -------------------------------------------------------

# node locations in pixel
NODES: Dict[int, Tuple[int, int]] = {
    1: (104, 110),
    2: (207, 70),
    3: (326, 31),
    4: (326, 99),
    5: (548, 69),
    6: (669, 85),
    7: (745, 177),
    8: (620, 363),
    # 9: (489, 320),
    10: (372, 395),
    11: (197, 337),
    12: (486, 375),
    13: (640, 180),
    14: (662, 225),
}

# -------------------------------------------------------


def indent(s, pre="\t", *, empty: bool = False):
    if empty:
        indent1 = lambda l: pre + l
    else:
        indent1 = lambda l: l if s.isspace() else pre + l
    return "\n".join(map(indent1, s.split("\n")))


class SVGNodes:
    def __init__(self, color="#FFFFFF"):
        self.color = color
        self._nodes = []

    @staticmethod
    def _gen_node(node, fill):
        x, y = NODES[node]
        return (
            f'<circle cx="{x}" cy="{y}" r="15" style="fill:{fill}"/>\n'
            f'<text transform="translate({x},{y})" dy=".36em" style="stroke:none">{node}</text>'
        )

    def add_node(self, node):
        self._nodes.append(self._gen_node(node, self.color))

    def get_svg_group(self):
        frame = (
            '<g style="fill:#000000;stroke:#000000;stroke-width:1;'
            'font:bold 17px sans-serif;text-anchor:middle">\n',
            "\n</g>\n",
        )
        data = "\n".join(self._nodes)
        return indent(data).join(frame)


class SVGLines:
    def __init__(self, color="#000000", width=1):
        self.color = color
        self.width = width
        self._lines = []

    @staticmethod
    def _gen_line(node1: int, node2: int, width):
        x1, y1 = NODES[node1]
        x2, y2 = NODES[node2]
        width = str(int(width))
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke-width:{width}"/>'

    def add_line(self, node1, node2, width=None):
        self._lines.append(self._gen_line(node1, node2, self.width if width is None else width))

    def get_svg_group(self):
        frame = (f'<g style="stroke:{self.color}">\n', "\n</g>\n")
        data = "\n".join(self._lines)
        return indent(data).join(frame)


def update_svg(group, file_inp: str, file_out: str) -> None:
    with Path(file_inp).open() as file:
        lines = file.readlines()
    k: int = 0
    i: int = 0
    for type_val in ("<svg", "<image"):
        while i < len(lines):
            if lines[i].strip().startswith(type_val):
                k = i + 1
                break
            i += 1
    lines.insert(k, group)
    logging.info("update file %s and save it to %s", file_inp, file_out)
    with Path(file_out).open("w") as file:
        file.writelines(lines)


# -------------------------------------------------------


def line_width(x_val: float) -> int:
    y_val = (100 + x_val + 4) // 5
    if x_val and not y_val:
        logging.warning("rssi of %s converted to line_width 1", x_val)
        return 1
    if y_val > 10:
        logging.warning("rssi of %s converted to line_width 10", x_val)
        y_val = 10
    return round(y_val)


def tpl_line_width(tpl) -> int:
    if abs(tpl[0] - tpl[1]) > 6:
        logging.warning("received and sent signal strength differ a lot: %s", tpl)
    return line_width(sum(tpl) // 2)


def add_nodes(file_inp: str, file_out: str) -> None:
    svgn = SVGNodes(color="#FFFF00")
    for n in NODES:
        svgn.add_node(n)
    update_svg("\n" + svgn.get_svg_group(), file_inp, file_out)


def add_links(file_inp: str, file_out: str, rssi: dict) -> None:
    svgl = SVGLines(color="#0000FF")
    rssi_tpls = {}
    for (n1, n2), v in rssi.items():
        tpl = rssi_tpls.setdefault((min(n1, n2), max(n1, n2)), [v - 10, v - 10])
        tpl[n2 > n1] = v
    for (n1, n2), tpl in rssi_tpls.items():
        svgl.add_line(n1, n2, tpl_line_width(tpl))
    update_svg("\n" + svgl.get_svg_group(), file_inp, file_out)


# -------------------------------------------------------


def extract_rssi_data(file_name: str) -> dict:
    data: list = []
    reading: bool = False
    with Path(file_name).open() as file:
        for line in file.readlines():
            if reading:
                if line.isspace():
                    break
                data.append(line)
            elif "link matrix:" in line.lower():
                reading = True
    logging.info("link matrix:\n%s", "".join(data))
    # extract numbers
    head = [(int(m[1]), m.span()) for m in re.finditer(r"\s+(\d+)", data[0])]
    assert len(head) == len(data) - 2
    rssi: dict = {}
    for line in data[2:]:
        m = re.match(r"^\s*(\d+)\s*\|", line)
        n1 = int(m[1])
        offset = m.span()[1]
        for n2, (a, b) in head:
            v = line[max(a, offset) : b].strip()
            if v:
                rssi[(n1, n2)] = float(v)
    return rssi


def check_outfile(file_inp: str, file_out: Optional[str] = None) -> str:
    if file_out is None:
        file = Path(file_inp).resolve()
        file_root = file.parent / file.stem
        file_ext = file.suffix
        return str(file_root) + "_" + os.urandom(2).hex() + file_ext
    if file_out == "":
        return file_inp
    return file_out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="visualize rssi links in an svg file")
    ap.add_argument("tbfile", type=str, help="TrafficBench trx_data.log file")
    ap.add_argument(
        "-s", "--svg", help="svg node file (default: nodes.svg)", type=str, default=INFILE
    )
    ap.add_argument(
        "-o",
        "--outfile",
        help="svg output (default: svg file with random tail)",
        type=str,
        default=None,
    )
    ap.add_argument("--add-nodes", help="add nodes to svg", action="store_true")
    args = ap.parse_args()
    args.outfile = check_outfile(args.svg, args.outfile)

    if args.add_nodes:
        logging.info("add nodes")
        add_nodes(args.svg, args.outfile)
        args.svg = args.outfile

    if args.tbfile:
        rssi_dic = extract_rssi_data(args.tbfile)
        add_links(args.svg, args.outfile, rssi_dic)
    else:
        logging.warning("no TrafficBench data defined")

    logging.info(f"svg file {args.outfile} created")
