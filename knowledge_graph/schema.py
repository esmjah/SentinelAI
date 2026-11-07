"""Node and edge types of the SentinelAI well-integrity knowledge graph (schema 1.0.0).

Asset view : ISO 14224-style hierarchy (Installation -> System -> Equipment unit -> Subunit ->
             Maintainable item -> Failure mechanism), containment volumes, formation zones,
             instrumentation (sensors, tags), tests, and the digital twin with its parameters.
Risk view  : NORSOK D-010-style barrier logic (Failure mode -> Barrier envelope -> Hazard),
             versioned limits, decision policy, and runtime assessments / decisions.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"


class View(str, Enum):
    ASSET = "asset"
    RISK = "risk"


class NodeType(str, Enum):
    # Asset view - structure
    INSTALLATION = "Installation"
    SYSTEM = "System"
    EQUIPMENT_UNIT = "EquipmentUnit"
    SUBUNIT = "Subunit"
    MAINTAINABLE_ITEM = "MaintainableItem"
    CONTAINMENT_VOLUME = "ContainmentVolume"
    FORMATION_ZONE = "FormationZone"
    EXTERNAL_DOMAIN = "ExternalDomain"
    FAILURE_MECHANISM = "FailureMechanism"
    # Asset view - evidence
    SENSOR = "Sensor"
    TAG = "Tag"
    VIRTUAL_TAG = "VirtualTag"
    SIMULATION_MODEL = "SimulationModel"
    MODEL_PARAMETER = "ModelParameter"
    TEST = "Test"
    # Risk view
    FAILURE_MODE = "FailureMode"
    BARRIER_ENVELOPE = "BarrierEnvelope"
    HAZARD = "Hazard"
    LIMIT = "Limit"
    DECISION_POLICY = "DecisionPolicy"
    RISK_ASSESSMENT = "RiskAssessment"   # written at runtime by pipeline/
    DECISION = "Decision"                # written at runtime by pipeline/


RISK_TYPES = {NodeType.FAILURE_MODE, NodeType.BARRIER_ENVELOPE, NodeType.HAZARD, NodeType.LIMIT,
              NodeType.DECISION_POLICY, NodeType.RISK_ASSESSMENT, NodeType.DECISION}
NODE_VIEW = {t: (View.RISK if t in RISK_TYPES else View.ASSET) for t in NodeType}


class EdgeType(str, Enum):
    # structure
    PART_OF = "PART_OF"                  # child -> parent (ISO 14224 hierarchy)
    BOUNDED_BY = "BOUNDED_BY"            # volume -> item forming one of its walls
    FLOWS_TO = "FLOWS_TO"                # process topology
    ACTUATES = "ACTUATES"                # safety system -> valve it can close
    HAS_MECHANISM = "HAS_MECHANISM"      # item or sensor -> failure mechanism
    CONNECTS = "CONNECTS"                # mechanism -> volume / zone / domain (role: src|snk)
    # instrumentation and data
    INSTALLED_ON = "INSTALLED_ON"        # sensor -> item / subunit / unit
    PRODUCED_BY = "PRODUCED_BY"          # tag -> sensor (measured) or test (manual reading)
    MEASURES = "MEASURES"                # tag -> node (property, location)
    ESTIMATES = "ESTIMATES"              # virtual tag -> node
    CONSUMES = "CONSUMES"                # model -> tag (input)
    PRODUCES = "PRODUCES"                # model -> virtual tag (output)
    HAS_PARAMETER = "HAS_PARAMETER"      # model -> uncertain parameter
    DESCRIBES = "DESCRIBES"              # parameter -> volume / item it belongs to
    SIMULATES = "SIMULATES"              # model -> failure mechanism it can inject
    # tests
    USES = "USES"                        # test -> tag / virtual tag
    EVIDENCE_FOR = "EVIDENCE_FOR"        # test -> failure mechanism
    MONITORS = "MONITORS"                # test -> failure mode (consequence monitoring)
    # cross-view
    CAUSES = "CAUSES"                    # failure mechanism -> failure mode
    MANIFESTS_IN = "MANIFESTS_IN"        # volume -> failure mode (no mechanism, e.g. thermal APB)
    IMPLEMENTED_BY = "IMPLEMENTED_BY"    # barrier envelope -> item (well barrier element)
    APPLIES_TO = "APPLIES_TO"            # limit -> volume
    LIMITED_BY = "LIMITED_BY"            # limit -> item whose rating sets it
    # risk view
    DEGRADES = "DEGRADES"                # failure mode -> barrier envelope
    AGGRAVATES = "AGGRAVATES"            # failure mode -> failure mode (compound risk)
    LEADS_TO = "LEADS_TO"                # barrier envelope or failure mode -> hazard
    CHECKED_AGAINST = "CHECKED_AGAINST"  # failure mode -> limit
    GOVERNS = "GOVERNS"                  # policy -> failure mode
    # runtime (pipeline/)
    ASSESSES = "ASSESSES"
    BASED_ON = "BASED_ON"
    RESULTS_IN = "RESULTS_IN"


CROSS_VIEW_EDGES = {EdgeType.CAUSES, EdgeType.MANIFESTS_IN, EdgeType.IMPLEMENTED_BY,
                    EdgeType.APPLIES_TO, EdgeType.LIMITED_BY}


class Node(BaseModel):
    id: str
    type: NodeType
    name: str
    props: dict = Field(default_factory=dict)

    @property
    def view(self) -> View:
        return NODE_VIEW[self.type]


class TestSpec(BaseModel):
    reliability: str            # "C" screening | "B" discriminating | "A" confirmatory
    cost_nok: float
    online: bool
    duration_h: float = 0.0
    description: str = ""


class LimitSpec(BaseModel):
    kind: str                   # MAASP (documented) | MAWOP (operating screen)
    value: float
    unit: str = "bar"
    revision: str
    effective_from: str
    source_doc: str
    basis: str = ""
    superseded_by: Optional[str] = None
