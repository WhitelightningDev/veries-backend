from __future__ import annotations

from enum import Enum


class VerificationAssetType(str, Enum):
    ID_DOCUMENT = "id_document"
    ID_DOCUMENT_FRONT = "id_document_front"
    ID_DOCUMENT_BACK = "id_document_back"
    SELFIE_WITH_ID = "selfie_with_id"
    BACKGROUND_VIDEO = "background_video"
