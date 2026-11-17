import re
from src.schema import InspectionRecord, Disposition, Severity


def check_business_rules(rec: InspectionRecord) -> list[str]:
    errors = []
    if not re.fullmatch(r"CB-\d{4}-[A-Z]", rec.part_id):
        errors.append("part_id does not match expected format")
    if rec.disposition == Disposition.REJECT and not rec.defects:
        errors.append("reject disposition requires at least one defect")
    if rec.disposition == Disposition.ACCEPT and any(
        d.severity == Severity.CRITICAL for d in rec.defects
    ):
        errors.append("accept disposition with a critical defect")
    return errors
