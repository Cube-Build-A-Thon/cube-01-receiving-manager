import hashlib

from backend.app.models.inspection import Inspection, InspectionCheck, ReceivingImage
from backend.app.models.po import PurchaseOrder
from backend.app.services.evidence_seal import build_sealed_evidence_record, canonical_content_hash


def _inspection(tmp_path, observed_quantity):
    image_path = tmp_path / "photo.png"
    image_path.write_bytes(b"inspection image bytes")
    return Inspection(
        inspection_id="INS-SEAL",
        po=PurchaseOrder(
            po_id="PO-SEAL",
            po_line="1",
            sku="SKU-1",
            asin="ASIN-1",
            product_name="Test item",
            expected_quantity=2,
            variant="blue",
            units_per_carton=1,
            expected_cartons=2,
        ),
        images=[
            ReceivingImage(
                image_id="IMG-SEAL",
                inspection_id="INS-SEAL",
                filename="photo.png",
                stored_filename="photo.png",
                image_path=str(image_path),
                image_type="front_view",
                mime_type="image/png",
            )
        ],
        checks=[
            InspectionCheck(
                check_name="quantity_check",
                status="PASS",
                expected_value=2,
                observed_value=observed_quantity,
                reason="Observed quantity matches.",
                confidence=0.99,
            )
        ],
        final_decision="PASS",
    )


def test_sealed_record_hash_changes_when_a_check_changes(tmp_path):
    inspection = _inspection(tmp_path, 2)
    first_record = build_sealed_evidence_record(inspection)
    inspection.checks[0].observed_value = 1
    second_record = build_sealed_evidence_record(inspection)

    assert first_record.content_hash != second_record.content_hash
    assert len(first_record.content_hash) == 64


def test_sealed_record_hash_is_canonical_and_image_digest_is_sha256(tmp_path):
    inspection = _inspection(tmp_path, 2)
    record = build_sealed_evidence_record(inspection)

    content = record.model_dump(mode="json", exclude={"content_hash"})
    assert record.content_hash == canonical_content_hash(content)
    assert record.images[0].sha256_digest == hashlib.sha256(b"inspection image bytes").hexdigest()
    assert record.recorded_at.utcoffset().total_seconds() == 0
    assert canonical_content_hash({"a": 1, "b": 2}) == canonical_content_hash({"b": 2, "a": 1})
