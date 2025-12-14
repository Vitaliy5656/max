"""
Templates Router for MAX AI API.

Endpoints:
- GET /api/templates
- POST /api/templates
"""
from fastapi import APIRouter

from src.core.templates import templates
from src.api.schemas import TemplateCreate

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates():
    """List all templates."""
    tpls = await templates.list_all()
    return [{
        "id": t.id,
        "name": t.name,
        "category": t.category or "general",
        "content": t.prompt
    } for t in tpls]


@router.post("")
async def create_template(data: TemplateCreate):
    """Create a new template."""
    tpl_id = await templates.save(data.name, data.prompt, data.category)
    return {"id": tpl_id, "name": data.name}
