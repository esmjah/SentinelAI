"""SentinelAI digital twin of synthetic well W01 (v1.0.0).

    from digital_twin import nominal_w01, Operations, Bleed, startup, simulate, failure_modes as fm
    res = simulate(nominal_w01(), Operations(bleeds=[Bleed(48)]), [fm.tubing_connection_leak()])
"""
from .config import TWIN_VERSION, WellConfig, AnnulusConfig, PipeRatings, nominal_w01, with_annulus
from .simulator import Operations, Bleed, startup, simulate, WellSimulator, SimResult, SIGNALS
from . import failure_modes
from .integrity import ELEMENTS_A, ELEMENTS_B
from .sensors import SensorSpec, DEFAULT_SENSORS, measure
from .uncertainty import PRIORS, sample_plant

__version__ = TWIN_VERSION
