"""Validate section-solid DXF structure (R12-compatible template)."""

import os
import tempfile
import unittest


def _dxf_line(code, value):
    return f"{code}\r\n{value}\r\n"


def _dxf_num(value):
    n = float(value)
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.6f}"


def build_section_solids_dxf(triangles):
    layers = {"0": True}
    for tri in triangles:
        layers[tri["layer"]] = True
    layer_names = sorted(layers.keys())

    xs = [tri[k] for tri in triangles for k in ("x1", "x2", "x3")]
    ys = [tri[k] for tri in triangles for k in ("y1", "y2", "y3")]
    zs = [tri[k] for tri in triangles for k in ("z1", "z2", "z3")]
    bounds = {
        "xmin": min(xs), "ymin": min(ys), "zmin": min(zs),
        "xmax": max(xs), "ymax": max(ys), "zmax": max(zs),
    }

    out = ""
    out += _dxf_line(999, "Structural Toolbox section solids")
    out += _dxf_line(0, "SECTION")
    out += _dxf_line(2, "HEADER")
    out += _dxf_line(9, "$ACADVER")
    out += _dxf_line(1, "AC1009")
    out += _dxf_line(9, "$INSBASE")
    out += _dxf_line(10, "0.0")
    out += _dxf_line(20, "0.0")
    out += _dxf_line(30, "0.0")
    out += _dxf_line(9, "$EXTMIN")
    out += _dxf_line(10, _dxf_num(bounds["xmin"]))
    out += _dxf_line(20, _dxf_num(bounds["ymin"]))
    out += _dxf_line(30, _dxf_num(bounds["zmin"]))
    out += _dxf_line(9, "$EXTMAX")
    out += _dxf_line(10, _dxf_num(bounds["xmax"]))
    out += _dxf_line(20, _dxf_num(bounds["ymax"]))
    out += _dxf_line(30, _dxf_num(bounds["zmax"]))
    out += _dxf_line(0, "ENDSEC")

    out += _dxf_line(0, "SECTION")
    out += _dxf_line(2, "TABLES")
    out += _dxf_line(0, "TABLE")
    out += _dxf_line(2, "LTYPE")
    out += _dxf_line(70, 1)
    out += _dxf_line(0, "LTYPE")
    out += _dxf_line(2, "CONTINUOUS")
    out += _dxf_line(70, 64)
    out += _dxf_line(3, "Solid line")
    out += _dxf_line(72, 65)
    out += _dxf_line(73, 0)
    out += _dxf_line(40, "0.0")
    out += _dxf_line(0, "ENDTAB")
    out += _dxf_line(0, "TABLE")
    out += _dxf_line(2, "LAYER")
    out += _dxf_line(70, len(layer_names))
    for name in layer_names:
        out += _dxf_line(0, "LAYER")
        out += _dxf_line(2, name)
        out += _dxf_line(70, 64)
        out += _dxf_line(62, 7)
        out += _dxf_line(6, "CONTINUOUS")
    out += _dxf_line(0, "ENDTAB")
    out += _dxf_line(0, "TABLE")
    out += _dxf_line(2, "STYLE")
    out += _dxf_line(70, 0)
    out += _dxf_line(0, "ENDTAB")
    out += _dxf_line(0, "ENDSEC")

    out += _dxf_line(0, "SECTION")
    out += _dxf_line(2, "BLOCKS")
    out += _dxf_line(0, "ENDSEC")

    out += _dxf_line(0, "SECTION")
    out += _dxf_line(2, "ENTITIES")
    for tri in triangles:
        out += _dxf_line(0, "3DFACE")
        out += _dxf_line(8, tri["layer"])
        out += _dxf_line(10, _dxf_num(tri["x1"]))
        out += _dxf_line(20, _dxf_num(tri["y1"]))
        out += _dxf_line(30, _dxf_num(tri["z1"]))
        out += _dxf_line(11, _dxf_num(tri["x2"]))
        out += _dxf_line(21, _dxf_num(tri["y2"]))
        out += _dxf_line(31, _dxf_num(tri["z2"]))
        out += _dxf_line(12, _dxf_num(tri["x3"]))
        out += _dxf_line(22, _dxf_num(tri["y3"]))
        out += _dxf_line(32, _dxf_num(tri["z3"]))
        out += _dxf_line(13, _dxf_num(tri["x3"]))
        out += _dxf_line(23, _dxf_num(tri["y3"]))
        out += _dxf_line(33, _dxf_num(tri["z3"]))
    out += _dxf_line(0, "ENDSEC")
    out += _dxf_line(0, "EOF")
    return out


class TestSectionSolidDxf(unittest.TestCase):
    def test_dxf_has_required_sections(self):
        triangles = [{
            "layer": "E1",
            "x1": 0.0, "y1": 0.0, "z1": 0.0,
            "x2": 1.0, "y2": 0.0, "z2": 0.0,
            "x3": 1.0, "y3": 1.0, "z3": 0.0,
        }]

        text = build_section_solids_dxf(triangles)
        self.assertIn("AC1009", text)
        self.assertIn("LTYPE", text)
        self.assertIn("CONTINUOUS", text)
        self.assertIn("BLOCKS", text)
        self.assertIn("3DFACE", text)
        self.assertTrue(text.endswith("EOF\r\n"))

        try:
            import ezdxf
        except ImportError:
            self.skipTest("ezdxf not installed")

        with tempfile.NamedTemporaryFile("w", suffix=".dxf", delete=False, encoding="ascii", newline="") as fh:
            fh.write(text)
            path = fh.name
        try:
            doc = ezdxf.readfile(path)
            faces = list(doc.modelspace().query("3DFACE"))
            self.assertEqual(len(faces), 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
