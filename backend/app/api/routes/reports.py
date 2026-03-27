"""
Endpoints de exportación de reportes.
Todos retornan archivos descargables (CSV o Excel).
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.models import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

# Todos los roles pueden descargar reportes
_any_role = require_roles("admin", "operator", "viewer")


@router.get("/consolidated", summary="Reporte consolidado (CSV)")
def download_consolidated_csv(
    current_user: User = Depends(_any_role),
    db: Session = Depends(get_db),
):
    """Descarga CSV con todos los resultados de la conciliación."""
    try:
        service = ReportService(db)
        content = service.generate_consolidated_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=conciliacion_completa.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")


@router.get("/inconsistencies", summary="Reporte de inconsistencias (CSV)")
def download_inconsistencies_csv(
    current_user: User = Depends(_any_role),
    db: Session = Depends(get_db),
):
    """Descarga CSV con registros que requieren revisión."""
    try:
        service = ReportService(db)
        content = service.generate_inconsistencies_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inconsistencias.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")


@router.get("/missing", summary="Reporte de faltantes (CSV)")
def download_missing_csv(
    current_user: User = Depends(_any_role),
    db: Session = Depends(get_db),
):
    """Descarga CSV con empleados sin transacción bancaria."""
    try:
        service = ReportService(db)
        content = service.generate_missing_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=faltantes.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")


@router.get("/extras", summary="Reporte de sobrantes (CSV)")
def download_extras_csv(
    current_user: User = Depends(_any_role),
    db: Session = Depends(get_db),
):
    """Descarga CSV con transacciones sin empleado en plantilla."""
    try:
        service = ReportService(db)
        content = service.generate_extras_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sobrantes.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")


@router.get("/consolidated-excel", summary="Reporte consolidado completo (Excel)")
def download_consolidated_excel(
    current_user: User = Depends(_any_role),
    db: Session = Depends(get_db),
):
    """
    Descarga Excel con múltiples hojas:
    Resumen, Todos, Inconsistencias, Faltantes, Sobrantes.
    """
    try:
        service = ReportService(db)
        content = service.generate_consolidated_excel()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=conciliacion_completa.xlsx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {e}")
