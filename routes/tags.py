from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db, Tag

router = APIRouter(tags=["tags"])


@router.get("/tags")
async def get_all_tags(db: Session = Depends(get_db)):
    """
    Get all available tags
    """
    tags = db.query(Tag).all()
    return [tag.to_dict() for tag in tags]
