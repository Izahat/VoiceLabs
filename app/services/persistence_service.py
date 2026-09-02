"""Application service that coordinates the database and media storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.persistence.models import Asset, Job, User, VoiceProfile
from infrastructure.persistence.repositories import (
    AssetRepository,
    JobRepository,
    UserRepository,
    VoiceProfileRepository,
)
from infrastructure.storage.file_storage import FileStorage, StoredFile


@dataclass(frozen=True)
class PersistedAsset:
    id: str
    path: str
    kind: str
    role: str
    original_filename: str
    mime_type: str | None
    size_bytes: int
    sha256: str


class PersistenceService:
    """Keep API handlers independent from SQLAlchemy and filesystem details."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: FileStorage,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage

    async def ensure_user(self, external_id: str | None) -> User:
        async with self.session_factory() as session:
            user = await UserRepository(session).get_or_create(external_id)
            await session.commit()
            return user

    async def create_job(
        self,
        *,
        user_id: str,
        kind: str,
        status: str,
        source_language: str | None = None,
        target_language: str | None = None,
        metadata: dict | None = None,
        job_id: str | None = None,
    ) -> Job:
        async with self.session_factory() as session:
            job = await JobRepository(session).create(
                user_id=user_id,
                kind=kind,
                status=status,
                source_language=source_language,
                target_language=target_language,
                metadata=metadata,
                job_id=job_id,
            )
            await session.commit()
            return job

    async def save_upload(
        self,
        upload,
        *,
        user_id: str,
        role: str,
        job_id: str | None = None,
        asset_id: str | None = None,
    ) -> PersistedAsset:
        asset_id = asset_id or uuid.uuid4().hex
        stored = await self.storage.save_upload(upload, user_id=user_id, asset_id=asset_id)
        return await self._persist_asset(
            user_id=user_id,
            role=role,
            job_id=job_id,
            asset_id=asset_id,
            stored=stored,
        )

    async def save_existing(
        self,
        source,
        *,
        user_id: str,
        role: str,
        original_filename: str,
        job_id: str | None = None,
        asset_id: str | None = None,
    ) -> PersistedAsset:
        asset_id = asset_id or uuid.uuid4().hex
        stored = self.storage.save_existing(
            source,
            user_id=user_id,
            asset_id=asset_id,
            original_filename=original_filename,
        )
        return await self._persist_asset(
            user_id=user_id,
            role=role,
            job_id=job_id,
            asset_id=asset_id,
            stored=stored,
        )

    async def _persist_asset(
        self,
        *,
        user_id: str,
        role: str,
        job_id: str | None,
        asset_id: str,
        stored: StoredFile,
    ) -> PersistedAsset:
        async with self.session_factory() as session:
            asset = await AssetRepository(session).create(
                user_id=user_id,
                path=stored.path,
                original_filename=stored.original_filename,
                kind=stored.kind,
                role=role,
                mime_type=stored.mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                job_id=job_id,
                asset_id=asset_id,
            )
            await session.commit()
            return self._asset_to_dto(asset)

    async def update_job(
        self,
        job_id: str,
        *,
        status: str,
        source_asset_id: str | None = None,
        output_asset_id: str | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> Job | None:
        async with self.session_factory() as session:
            job = await JobRepository(session).update_status(
                job_id,
                status=status,
                source_asset_id=source_asset_id,
                output_asset_id=output_asset_id,
                error_message=error_message,
                metadata=metadata,
            )
            await session.commit()
            return job

    async def create_voice_profile(
        self,
        *,
        user_id: str,
        reference_asset_id: str,
        reference_text: str,
        profile_id: str,
    ) -> VoiceProfile:
        async with self.session_factory() as session:
            profile = await VoiceProfileRepository(session).create(
                user_id=user_id,
                reference_asset_id=reference_asset_id,
                reference_text=reference_text,
                profile_id=profile_id,
            )
            await session.commit()
            return profile

    async def get_job(self, job_id: str) -> Job | None:
        async with self.session_factory() as session:
            return await JobRepository(session).get(job_id)

    async def list_jobs(self, user_id: str, limit: int = 50) -> list[Job]:
        async with self.session_factory() as session:
            return await JobRepository(session).list_for_user(user_id, limit=limit)

    async def get_asset(self, asset_id: str) -> Asset | None:
        async with self.session_factory() as session:
            return await AssetRepository(session).get(asset_id)

    async def get_voice_profile(self, profile_id: str) -> VoiceProfile | None:
        async with self.session_factory() as session:
            return await VoiceProfileRepository(session).get(profile_id)

    @staticmethod
    def _asset_to_dto(asset: Asset) -> PersistedAsset:
        return PersistedAsset(
            id=asset.id,
            path=asset.stored_path,
            kind=asset.kind,
            role=asset.role,
            original_filename=asset.original_filename,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            sha256=asset.sha256,
        )
