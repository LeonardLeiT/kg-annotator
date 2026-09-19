from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .api import router
from .config import get_settings
from .db import Base, SessionLocal, engine
from .services.annotations import backfill_annotation_revisions


def create_app() -> FastAPI:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # create_all does not add columns to an existing SQLite table.
    if "context_role" not in {column["name"] for column in inspect(engine).get_columns("entity_mentions")}:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE entity_mentions ADD COLUMN context_role VARCHAR(16) NOT NULL DEFAULT 'current'"
            ))
    with SessionLocal() as db:
        backfill_annotation_revisions(db)
    app = FastAPI(title="KG Annotator API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
