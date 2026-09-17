"""
Algorise 100 Hero Bots Master Solvers Package
Aggregates all 100 individual Python solvers and JavaScript solver code strings across all 10 sectors.
"""

from .sector1_agriculture import SECTOR1_PY_SOLVERS, SECTOR1_JS_SOLVERS
from .sector2_enterprise import SECTOR2_PY_SOLVERS, SECTOR2_JS_SOLVERS
from .sector3_retail import SECTOR3_PY_SOLVERS, SECTOR3_JS_SOLVERS
from .sector4_creator import SECTOR4_PY_SOLVERS, SECTOR4_JS_SOLVERS
from .sector5_healthcare import SECTOR5_PY_SOLVERS, SECTOR5_JS_SOLVERS
from .sector6_realestate import SECTOR6_PY_SOLVERS, SECTOR6_JS_SOLVERS
from .sector7_finance import SECTOR7_PY_SOLVERS, SECTOR7_JS_SOLVERS
from .sector8_legal import SECTOR8_PY_SOLVERS, SECTOR8_JS_SOLVERS
from .sector9_logistics import SECTOR9_PY_SOLVERS, SECTOR9_JS_SOLVERS
from .sector10_education import SECTOR10_PY_SOLVERS, SECTOR10_JS_SOLVERS

ALL_100_PY_SOLVERS = {}
ALL_100_JS_SOLVERS = {}

for s in [
    (SECTOR1_PY_SOLVERS, SECTOR1_JS_SOLVERS),
    (SECTOR2_PY_SOLVERS, SECTOR2_JS_SOLVERS),
    (SECTOR3_PY_SOLVERS, SECTOR3_JS_SOLVERS),
    (SECTOR4_PY_SOLVERS, SECTOR4_JS_SOLVERS),
    (SECTOR5_PY_SOLVERS, SECTOR5_JS_SOLVERS),
    (SECTOR6_PY_SOLVERS, SECTOR6_JS_SOLVERS),
    (SECTOR7_PY_SOLVERS, SECTOR7_JS_SOLVERS),
    (SECTOR8_PY_SOLVERS, SECTOR8_JS_SOLVERS),
    (SECTOR9_PY_SOLVERS, SECTOR9_JS_SOLVERS),
    (SECTOR10_PY_SOLVERS, SECTOR10_JS_SOLVERS),
]:
    ALL_100_PY_SOLVERS.update(s[0])
    ALL_100_JS_SOLVERS.update(s[1])

print(f"Aggregated {len(ALL_100_PY_SOLVERS)} Python solvers and {len(ALL_100_JS_SOLVERS)} JavaScript solvers.")
