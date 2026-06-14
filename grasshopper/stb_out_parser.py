"""Parse Structural Toolbox .out files for Grasshopper.

The text output is comma-separated and record-oriented. Keeping this parser
small makes it easy to port the same behavior to the C# .gha component.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class NodalDisplacement:
    load_case: int
    node_id: int
    x: float
    y: float
    z: float
    theta_x: float
    theta_y: float
    theta_z: float


@dataclass
class ReactionForce:
    load_case: int
    node_id: int
    tx: float
    ty: float
    tz: float
    rx: float
    ry: float
    rz: float


@dataclass
class ElementForce:
    load_case: int
    element_id: int
    ni: float
    qyi: float
    qzi: float
    mxi: float
    myi: float
    mzi: float
    nj: float
    qyj: float
    qzj: float
    mxj: float
    myj: float
    mzj: float
    myc: float
    mzc: float


@dataclass
class StbResults:
    displacements: List[NodalDisplacement]
    reactions: List[ReactionForce]
    element_forces: List[ElementForce]

    @property
    def load_cases(self) -> List[int]:
        values = {row.load_case for row in self.displacements}
        values.update(row.load_case for row in self.reactions)
        values.update(row.load_case for row in self.element_forces)
        return sorted(values)


def _parts(line: str) -> List[str]:
    return [part.strip() for part in line.split(",")]


def parse_stb_out_lines(lines: Iterable[str], load_case: Optional[int] = None) -> StbResults:
    displacements: List[NodalDisplacement] = []
    reactions: List[ReactionForce] = []
    element_forces: List[ElementForce] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = _parts(line)
        record = parts[0]

        if record == "NDSP" and len(parts) >= 9:
            lc = int(parts[1])
            if load_case is not None and lc != load_case:
                continue
            displacements.append(
                NodalDisplacement(
                    load_case=lc,
                    node_id=int(parts[2]),
                    x=float(parts[3]),
                    y=float(parts[4]),
                    z=float(parts[5]),
                    theta_x=float(parts[6]),
                    theta_y=float(parts[7]),
                    theta_z=float(parts[8]),
                )
            )
        elif record == "REAC" and len(parts) >= 9:
            lc = int(parts[1])
            if load_case is not None and lc != load_case:
                continue
            reactions.append(
                ReactionForce(
                    load_case=lc,
                    node_id=int(parts[2]),
                    tx=float(parts[3]),
                    ty=float(parts[4]),
                    tz=float(parts[5]),
                    rx=float(parts[6]),
                    ry=float(parts[7]),
                    rz=float(parts[8]),
                )
            )
        elif record == "EFRC" and len(parts) >= 17:
            lc = int(parts[1])
            if load_case is not None and lc != load_case:
                continue
            element_forces.append(
                ElementForce(
                    load_case=lc,
                    element_id=int(parts[2]),
                    ni=float(parts[3]),
                    qyi=float(parts[4]),
                    qzi=float(parts[5]),
                    mxi=float(parts[6]),
                    myi=float(parts[7]),
                    mzi=float(parts[8]),
                    nj=float(parts[9]),
                    qyj=float(parts[10]),
                    qzj=float(parts[11]),
                    mxj=float(parts[12]),
                    myj=float(parts[13]),
                    mzj=float(parts[14]),
                    myc=float(parts[15]),
                    mzc=float(parts[16]),
                )
            )

    return StbResults(
        displacements=displacements,
        reactions=reactions,
        element_forces=element_forces,
    )


def parse_stb_out_file(path: str, load_case: Optional[int] = None) -> StbResults:
    with open(path, "r", encoding="utf-8") as f:
        return parse_stb_out_lines(f, load_case=load_case)
