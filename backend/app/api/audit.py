import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from ..db.database import get_db
from ..models import models
from ..api.auth import get_current_user_with_role, RoleEnum

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)

@router.get("/export")
async def export_audit_log(
    format: str = Query("csv", pattern="^(csv)$"),
    from_date: datetime = Query(None),
    to_date: datetime = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    """Exports the audit trail for bias and screening decisions."""
    stmt = select(models.AuditLog).where(models.AuditLog.user_id == current_user.id) # Filter by org/user
    
    if from_date:
        stmt = stmt.where(models.AuditLog.created_at >= from_date)
    if to_date:
        stmt = stmt.where(models.AuditLog.created_at <= to_date)
        
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Action", "Entity Type", "Entity ID", 
        "Model Version", "Input Hash", "Output Summary", "Bias Flags", "Created At"
    ])
    
    for log in logs:
        writer.writerow([
            log.id, log.action, log.entity_type, log.entity_id,
            log.model_version, log.input_hash, 
            str(log.output_json.get("total_score", "N/A")),
            str(log.bias_flags),
            log.created_at.isoformat()
        ])
        
    output.seek(0)
    filename = f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
