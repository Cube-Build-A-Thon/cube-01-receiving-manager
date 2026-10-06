from backend.app.core.decision_engine import evaluate_component_check
from backend.app.models.inspection import Inspection
from backend.app.models.po import PurchaseOrder
from backend.app.services.vision import (
    VisionAnalysisResponse,
    VisionImageResult,
    VisionObservationItem,
    VisionService,
)


def _vision_service():
    return VisionService(
        Inspection(
            inspection_id="INS-TEST",
            po=PurchaseOrder(
                po_id="PO-TEST",
                sku="BLUE-BOTTLE-001",
                product_name="Blue Bottle",
                expected_quantity=24,
                variant="Blue",
                units_per_carton=12,
                expected_cartons=2,
                expected_components=["cap", "label"],
            ),
        )
    )


def _vision_payload(*image_observations):
    return VisionAnalysisResponse(
        images=[
            VisionImageResult(
                image_id=f"image-{index}",
                visibility="clear",
                observations=[
                    VisionObservationItem(
                        check_type=check_type,
                        observation=observation,
                        confidence=0.9,
                        description="Visible reading.",
                    )
                    for check_type, observation in observations
                ],
            )
            for index, observations in enumerate(image_observations, start=1)
        ]
    )


def test_missing_carton_count_is_uncertain():
    service = _vision_service()
    checks = service._build_checks(_vision_payload([("quantity", 24), ("units_per_carton", 12)]))
    carton_check = next(check for check in checks if check.check_name == "carton_check")
    assert carton_check.status == "UNCERTAIN"
    assert carton_check.observed_value is None


def test_uncertain_damage_is_preserved_as_uncertain():
    checks = _vision_service()._build_checks(_vision_payload([("damage", "uncertain")]))
    damage_check = next(check for check in checks if check.check_name == "damage_check")
    assert damage_check.status == "UNCERTAIN"


def test_clear_damage_reading_passes():
    checks = _vision_service()._build_checks(_vision_payload([("damage", "none")]))
    damage_check = next(check for check in checks if check.check_name == "damage_check")
    assert damage_check.status == "PASS"


def test_list_shaped_damage_observation_does_not_raise():
    result = _vision_service()._build_result(_vision_payload([("damage", ["crushing"])]))
    damage_check = next(check for check in result["checks"] if check["check_name"] == "damage_check")
    assert damage_check["status"] == "FAIL"


def test_disagreeing_photo_quantity_is_uncertain():
    checks = _vision_service()._build_checks(_vision_payload([("quantity", 24)], [("quantity", 22)]))
    quantity_check = next(check for check in checks if check.check_name == "quantity_check")
    assert quantity_check.status == "UNCERTAIN"


def test_no_required_components_are_not_required():
    assert evaluate_component_check([], [])["status"] == "NOT_REQUIRED"


def test_quantity_cartons_and_units_per_carton_are_checked_separately():
    service = _vision_service()
    result = service._build_checks(_vision_payload([("quantity", 20), ("carton", 2), ("units_per_carton", 10)]))
    checks = {check.check_name: check.status for check in result}
    assert checks["quantity_check"] == "FAIL"
    assert checks["carton_check"] == "PASS"
    assert checks["units_per_carton_check"] == "FAIL"


def test_matching_quantity_cartons_and_units_per_carton_pass():
    service = _vision_service()
    result = service._build_checks(_vision_payload([("quantity", 24), ("carton", 2), ("units_per_carton", 12)]))
    checks = {check.check_name: check.status for check in result}
    assert checks["quantity_check"] == "PASS"
    assert checks["carton_check"] == "PASS"
    assert checks["units_per_carton_check"] == "PASS"
