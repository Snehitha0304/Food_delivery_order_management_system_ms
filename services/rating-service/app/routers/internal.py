from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.rating import AgentAverageRatingResponse
from app.security import verify_internal_api_key
from app.services.rating_service import rating_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/ratings/agents/averages", response_model=List[AgentAverageRatingResponse])
def internal_get_agent_averages(db: Session = Depends(get_db)):
    return rating_service.get_all_agent_averages(db)
