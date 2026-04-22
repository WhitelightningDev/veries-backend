from __future__ import annotations

import cv2
import numpy as np

from veries_backend.app.domain.verification_assets.types import VerificationAssetType
from veries_backend.app.services.asset_vision import AssetVisionService, VisionSettings


def _encode_png(bgr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", bgr)
    assert ok
    return bytes(buf)


def test_vision_rejects_non_decodable_image_when_required() -> None:
    svc = AssetVisionService(settings=VisionSettings(require_decodable_images=True))
    result = svc.analyze_upload(
        asset_type=VerificationAssetType.ID_DOCUMENT,
        mime_type="image/jpeg",
        data=b"not-a-real-image",
    )
    assert result["should_reject"] is True
    assert "decode_failed" in result["issues"]


def test_vision_detects_document_area_ratio_for_id_document() -> None:
    svc = AssetVisionService(
        settings=VisionSettings(
            enforce_quality=True,
            min_image_side_px=1,
            min_document_area_ratio=0.1,
            min_blur_variance=0.0,
            max_glare_ratio=1.0,
            min_brightness=0.0,
            max_brightness=255.0,
        )
    )

    img = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.rectangle(img, (80, 60), (720, 540), (255, 255, 255), thickness=6)
    data = _encode_png(img)

    result = svc.analyze_upload(
        asset_type=VerificationAssetType.ID_DOCUMENT,
        mime_type="image/png",
        data=data,
    )
    assert result["should_reject"] is False
    assert result["metrics"]["document_area_ratio"] >= 0.1

