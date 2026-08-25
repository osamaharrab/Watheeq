from fastapi import APIRouter

from app.schema_registry import get_queryable_schema
from app.schemas import SchemaResponse


router = APIRouter(prefix="/api/v1")


@router.get("/schema", response_model=SchemaResponse)
def schema() -> SchemaResponse:
    return SchemaResponse(**get_queryable_schema())
