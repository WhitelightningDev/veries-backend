from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from veries_backend.app.domain.verification_assets.types import VerificationAssetType


@dataclass(frozen=True, slots=True)
class VisionSettings:
    enabled: bool = True
    require_decodable_images: bool = True
    enforce_quality: bool = False

    min_image_side_px: int = 600
    max_glare_ratio: float = 0.12
    min_blur_variance: float = 60.0
    min_brightness: float = 40.0
    max_brightness: float = 220.0

    # Selfie
    max_faces: int = 1
    min_face_area_ratio: float = 0.02

    # ID document
    min_document_area_ratio: float = 0.25


class AssetVisionService:
    def __init__(self, *, settings: VisionSettings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    def analyze_upload(
        self,
        *,
        asset_type: VerificationAssetType,
        mime_type: str,
        data: bytes,
    ) -> dict[str, Any]:
        """
        OpenCV-based upload checks intended to improve reliability and reduce obvious abuse.

        Result is safe to JSON-serialize and can be attached to event metadata.
        """
        s = self._settings
        if not s.enabled:
            return {"enabled": False, "skipped": True, "reason": "disabled"}

        mime_type = (mime_type or "").lower().strip()
        if mime_type in {"application/pdf", "image/heic", "image/heif"}:
            return {
                "enabled": True,
                "skipped": True,
                "reason": "unsupported_mime",
                "mime_type": mime_type,
            }

        if mime_type not in {"image/jpeg", "image/jpg", "image/png"}:
            return {
                "enabled": True,
                "skipped": True,
                "reason": "not_an_image",
                "mime_type": mime_type,
            }

        if not data:
            return {
                "enabled": True,
                "skipped": False,
                "ok": False,
                "should_reject": True,
                "issues": ["empty_file"],
                "metrics": {},
            }

        image = _decode_bgr(data)
        if image is None:
            # If the client says it's an image but we can't decode it, reject (configurable).
            should_reject = bool(s.require_decodable_images)
            return {
                "enabled": True,
                "skipped": False,
                "ok": False,
                "should_reject": should_reject,
                "issues": ["decode_failed"],
                "metrics": {},
            }

        height, width = image.shape[:2]
        gray = _to_gray(image)

        metrics: dict[str, Any] = {
            "width": int(width),
            "height": int(height),
        }

        issues: list[str] = []

        if min(width, height) < s.min_image_side_px:
            issues.append("too_small")

        blur_var = _blur_variance(gray)
        metrics["blur_variance"] = float(blur_var)
        if blur_var < s.min_blur_variance:
            issues.append("too_blurry")

        brightness = float(gray.mean())
        metrics["brightness_mean"] = brightness
        if brightness < s.min_brightness:
            issues.append("too_dark")
        elif brightness > s.max_brightness:
            issues.append("too_bright")

        glare_ratio = _glare_ratio(gray)
        metrics["glare_ratio"] = float(glare_ratio)
        if glare_ratio > s.max_glare_ratio:
            issues.append("glare_high")

        if asset_type == VerificationAssetType.SELFIE_WITH_ID:
            face_count, face_area_ratio = _detect_faces(gray)
            metrics["face_count"] = int(face_count)
            if face_area_ratio is not None:
                metrics["face_area_ratio"] = float(face_area_ratio)

            if face_count == 0:
                issues.append("no_face_detected")
            elif face_count > s.max_faces:
                issues.append("multiple_faces")
            elif face_area_ratio is not None and face_area_ratio < s.min_face_area_ratio:
                issues.append("face_too_small")

        if asset_type in {
            VerificationAssetType.ID_DOCUMENT,
            VerificationAssetType.ID_DOCUMENT_FRONT,
            VerificationAssetType.ID_DOCUMENT_BACK,
        }:
            doc_area_ratio = _detect_document_area_ratio(gray)
            if doc_area_ratio is not None:
                metrics["document_area_ratio"] = float(doc_area_ratio)
            if doc_area_ratio is None:
                issues.append("document_not_detected")
            elif doc_area_ratio < s.min_document_area_ratio:
                issues.append("document_too_small")

        # Enforce policy: always enforce decoding when configured; quality checks are optional.
        should_reject = False
        if "empty_file" in issues or "decode_failed" in issues:
            should_reject = True
        elif s.enforce_quality and issues:
            should_reject = True

        ok = not issues
        return {
            "enabled": True,
            "skipped": False,
            "ok": ok,
            "should_reject": should_reject,
            "issues": issues,
            "metrics": metrics,
        }


def _decode_bgr(data: bytes):
    import cv2
    import numpy as np

    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _to_gray(bgr):
    import cv2

    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def _blur_variance(gray) -> float:
    import cv2

    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _glare_ratio(gray) -> float:
    # fraction of pixels that are near-white (highlights/glare)
    import numpy as np

    return float((gray >= 250).mean()) if isinstance(gray, np.ndarray) else 0.0


@lru_cache(maxsize=1)
def _face_cascade():
    import cv2

    cascade_path = f"{cv2.data.haarcascades}haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(cascade_path)


def _detect_faces(gray) -> tuple[int, float | None]:
    import cv2

    faces = _face_cascade().detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        flags=cv2.CASCADE_SCALE_IMAGE,
        minSize=(40, 40),
    )
    face_count = int(len(faces))
    if face_count == 0:
        return 0, None

    h, w = gray.shape[:2]
    image_area = float(h * w) if h and w else 0.0
    if image_area <= 0.0:
        return face_count, None

    biggest_area = 0.0
    for (_, _, fw, fh) in faces:
        biggest_area = max(biggest_area, float(fw * fh))
    return face_count, biggest_area / image_area


def _detect_document_area_ratio(gray) -> float | None:
    import cv2

    h, w = gray.shape[:2]
    if h < 2 or w < 2:
        return None

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 75, 200)
    contours, _hier = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    image_area = float(h * w)
    best_area = 0.0

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4:
            continue
        area = float(cv2.contourArea(approx))
        if area > best_area:
            best_area = area

    if best_area <= 0.0:
        return None

    return best_area / image_area
