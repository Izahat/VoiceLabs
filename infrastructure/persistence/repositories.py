"""Small repository layer keeping SQLAlchemy out of API handlers."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models import Asset, Job, User, VoiceProfile


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, external_id: str | None = None) -> User:
        external_id = external_id or "anonymous"
        result = await self.session.execute(select(User).where(User.external_id == external_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(id=uuid.uuid4().hex, external_id=external_id)
        self.session.add(user)
        await self.session.flush()
        return user


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        kind: str,
        status: str,
        source_language: str | None = None,
        target_language: str | None = None,
        source_asset_id: str | None = None,
        metadata: dict | None = None,
        job_id: str | None = None,
    ) -> Job:
        job = Job(
            id=job_id or uuid.uuid4().hex,
            user_id=user_id,
            kind=kind,
            status=status,
            source_language=source_language,
            target_language=target_language,
            source_asset_id=source_asset_id,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_status(
        self,
        job_id: str,
        *,
        status: str,
        source_asset_id: str | None = None,
        output_asset_id: str | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> Job | None:
        job = await self.session.get(Job, job_id)
        if job is None:
            return None
        job.status = status
        if source_asset_id is not None:
            job.source_asset_id = source_asset_id
        job.output_asset_id = output_asset_id
        job.error_message = error_message
        if metadata is not None:
            job.metadata_json = json.dumps(metadata, ensure_ascii=False)
        await self.session.flush()
        return job

    async def get(self, job_id: str) -> Job | None:
        return await self.session.get(Job, job_id)

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(desc(Job.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        path: Path,
        original_filename: str,
        kind: str,
        role: str,
        mime_type: str | None,
        size_bytes: int,
        sha256: str,
        job_id: str | None = None,
        asset_id: str | None = None,
    ) -> Asset:
        asset = Asset(
            id=asset_id or uuid.uuid4().hex,
            user_id=user_id,
            job_id=job_id,
            kind=kind,
            role=role,
            original_filename=original_filename,
            stored_path=str(path),
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
        )
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def get(self, asset_id: str) -> Asset | None:
        return await self.session.get(Asset, asset_id)


class VoiceProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        reference_asset_id: str,
        reference_text: str,
        profile_id: str | None = None,
    ) -> VoiceProfile:
        profile = VoiceProfile(
            id=profile_id or uuid.uuid4().hex[:12],
            user_id=user_id,
            reference_asset_id=reference_asset_id,
            reference_text=reference_text,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get(self, profile_id: str) -> VoiceProfile | None:
        return await self.session.get(VoiceProfile, profile_id)
