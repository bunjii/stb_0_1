import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
CLASSES = os.path.join(ROOT, "classes")
if CLASSES not in sys.path:
    sys.path.insert(0, CLASSES)

from stb_gui.loads_view import _load_model_and_project, build_seismic_loads_view, build_wind_loads_view
from stb_loads.equilibrium import compute_seismic_equilibrium
from stb_loads.format import _check_vertical_weight_reactions, build_seismic_report_view
from stb_loads import compute_seismic_distribution, compute_wind_distribution

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/UK_240416_floors_1to3_rigid_diaphragm.dat"


def bench(label, fn):
    t0 = time.perf_counter()
    fn()
    ms = (time.perf_counter() - t0) * 1000
    print(f"{label}: {ms:.0f} ms")


print("model:", PATH)
bench("parse+project (cold)", lambda: _load_model_and_project(PATH))
dat_relpath, full, mdl, project = _load_model_and_project(PATH)
bench("parse+project (cached)", lambda: _load_model_and_project(PATH))

result = compute_seismic_distribution(mdl, project)
bench("build_seismic_report_view", lambda: build_seismic_report_view(result, project, mdl=mdl))
bench("build_seismic_loads_view TOTAL", lambda: build_seismic_loads_view(mdl, project, dat_relpath))

result_w = compute_wind_distribution(mdl, project)
bench("build_wind_loads_view TOTAL (1st)", lambda: build_wind_loads_view(mdl, project, dat_relpath, include_visual=False))
bench("build_wind_loads_view TOTAL (2nd, solved cache)", lambda: build_wind_loads_view(mdl, project, dat_relpath, include_visual=False))
bench("build_seismic_loads_view TOTAL (2nd, solved cache)", lambda: build_seismic_loads_view(mdl, project, dat_relpath))
