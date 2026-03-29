from sqlalchemy.orm import Session

from app.db.model.error_log_model import ErrorLog


def save_error_log(
    db: Session,
    container_name: str,
    raw_error_log_line: str,
    suggested_command: str,
    confidence: float,
) -> ErrorLog:
    record = ErrorLog(
        container_name=container_name,
        raw_error_log_line=raw_error_log_line,
        suggested_command=suggested_command,
        confidence=float(confidence),
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record