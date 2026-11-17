from enum import Enum
from pydantic import BaseModel, Field


class DefectType(str, Enum):
    POROSITY = "porosity"
    INCLUSION = "inclusion"
    SHRINKAGE = "shrinkage"
    CRACK = "crack"


class Severity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class Disposition(str, Enum):
    ACCEPT = "accept"
    REWORK = "rework"
    REJECT = "reject"


class Defect(BaseModel):
    type: DefectType
    location: str
    severity: Severity


class InspectionRecord(BaseModel):
    part_id: str
    casting_type: str | None = None
    defects: list[Defect] = Field(default_factory=list)
    disposition: Disposition
