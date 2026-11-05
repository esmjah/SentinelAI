"""Node and edge types for the two coupled views.

Asset view : ISO 14224-style hierarchy (Installation -> System -> Equipment unit ->
             Subunit -> Maintainable item -> Failure mechanism) + tags, tests, twin.
Risk view  : NORSOK D-010-style barrier logic (Failure mode -> Barrier envelope ->
             Hazard) + versioned limits + runtime assessments and decisions.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"


class View(str, Enum):
    ASSET = "asset"
    RISK = "risk"


class NodeType(str, Enum):
    # Asset view - hierarchy
    INSTALLATION = "Installation"
    SYSTEM = "System"
    EQUIPMENT_UNIT = "EquipmentUnit"
    SUBUNIT = "Subunit"
    CONTAINMENT_VOLUME = "ContainmentVolume"
    MAINTAINABLE_ITEM = "MaintainableItem"
    FAILURE_MECHANISM = "FailureMechanism"
    # Asset view - evidence
    SENSOR = "Sensor"
    TAG = "Tag"
    VIRTUAL_TAG = "VirtualTag"
    SIMULATION_MODEL = "SimulationModel"
    TEST = "Test"
    # Risk view
    FAILURE_MODE = "FailureMode"
    BARRIER_ENVELOPE = "BarrierEnvelope"
    HAZARD = "Hazard"
    LIMIT = "Limit"
    DECISION_POLICY = "DecisionPolicy"
    RISK_ASSESSMENT = "RiskAssessment"   # created at runtime by pipeline/
    DECISION = "Decision"                # created at runtime by pipeline/


NODE_VIEW = {t: View.RISK for t in [NodeType.FAILURE_MODE, NodeType.BARRIER_ENVELOPE, NodeType.HAZARD,
                                    NodeType.LIMIT, NodeType.DECISION_POLICY,
                                    NodeType.RISK_ASSESSMENT, NodeType.DECISION]}
for _t in NodeType:
    NODE_VIEW.setdefault(_t, View.ASSET)


class EdgeType(str, Enum):
    PART_OF = "PART_OF"                  # hierarchy, child -> parent
    BOUNDED_BY = "BOUNDED_BY"            # volume -> item forming its wall
    FLOWS_TO = "FLOWS_TO"                # process topology
    HAS_MECHANISM = "HAS_MECHANISM"      # item -> failure mechanism
    INSTALLED_ON = "INSTALLED_ON"        # sensor -> item / volume
    PRODUCED_BY = "PRODUCED_BY"          # tag -> sensor
    MEASURES = "MEASURES"                # tag -> item / volume
    CONSUMES = "CONSUMES"                # model -> tag
    PRODUCES = "PRODUCES"                # model -> virtual tag
    ESTIMATES = "ESTIMATES"              # virtual tag -> item / volume
    USES = "USES"                        # test -> tag / virtual tag
    EVIDENCE_FOR = "EVIDENCE_FOR"        # test -> failure mechanism
    # cross-view
    CAUSES = "CAUSES"                    # failure mechanism -> failure mode
    MANIFESTS_IN = "MANIFESTS_IN"        # volume -> failure mode (non-mechanism, e.g. thermal APB)
    IMPLEMENTED_BY = "IMPLEMENTED_BY"    # barrier envelope -> maintainable item
    APPLIES_TO = "APPLIES_TO"            # limit -> volume
    # risk view
    DEGRADES = "DEGRADES"                # failure mode -> barrier envelope
    LEADS_TO = "LEADS_TO"                # barrier envelope -> hazard
    CHECKED_AGAINST = "CHECKED_AGAINST"  # failure mode -> limit
    GOVERNS = "GOVERNS"                  # policy -> failure mode
    # runtime (pipeline/)
    ASSESSES = "ASSESSES"
    BASED_ON = "BASED_ON"
    RESULTS_IN = "RESULTS_IN"


CROSS_VIEW_EDGES = {EdgeType.CAUSES, EdgeType.MANIFESTS_IN, EdgeType.IMPLEMENTED_BY, EdgeType.APPLIES_TO}


class Node(BaseModel):
    """Every node has a stable id, a type and a human name; extra props are typed by usage."""
    id: str
    type: NodeType
    name: str
    props: dict = Field(default_factory=dict)

    @property
    def view(self) -> View:
        return NODE_VIEW[self.type]


class Edge(BaseModel):
    src: str
    dst: str
    type: EdgeType
    props: dict = Field(default_factory=dict)


class TestSpec(BaseModel):
    reliability: str                     # "A" confirmatory, "B" discriminating, "C" screening
    cost_nok: float
    online: bool
    description: str


class LimitSpec(BaseModel):
    value: float
    unit: str
    revision: str
    effective_from: str
    source_doc: str
    superseded_by: Optional[str] = None
