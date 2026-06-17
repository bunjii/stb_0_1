import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "classes"))

from stb_gui.loads_view import load_seismic_view_for_model, load_wind_view_for_model
from stb_gui.model_json import load_model_dict
from stb_gui.model_session import invalidate_model_session, get_parsed_model
from stb_loads.equilibrium import _SOLVED_MODEL_CACHE, invalidate_solved_model_cache
from stb_gui.model_json import resolve_model_path

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/UK_240416_floors_1to3_rigid_diaphragm.dat"
FULL = resolve_model_path(PATH)


def ms(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def reset():
    invalidate_model_session(FULL)
    invalidate_solved_model_cache(FULL)
    _SOLVED_MODEL_CACHE.clear()


print("model:", PATH)

reset()
print(f"loads seismic (fully cold): {ms(lambda: load_seismic_view_for_model(PATH)):.0f} ms")

reset()
load_model_dict(PATH, solve=False)
print(f"loads seismic (parse warm, like viewer open): {ms(lambda: load_seismic_view_for_model(PATH)):.0f} ms")

reset()
load_model_dict(PATH, solve=True)
print(f"loads seismic (parse+solve warm, after Solve): {ms(lambda: load_seismic_view_for_model(PATH)):.0f} ms")

reset()
load_model_dict(PATH, solve=False)
load_seismic_view_for_model(PATH)
print(f"wind tab (after seismic, caches warm): {ms(lambda: load_wind_view_for_model(PATH, include_visual=False)):.0f} ms")
