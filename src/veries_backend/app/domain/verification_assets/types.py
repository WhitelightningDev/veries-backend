from __future__ import annotations

from enum import Enum


class VerificationAssetType(str, Enum):
    ID_DOCUMENT = "id_document"
    SELFIE_WITH_ID = "selfie_with_id"
    BACKGROUND_VIDEO = "background_video"
