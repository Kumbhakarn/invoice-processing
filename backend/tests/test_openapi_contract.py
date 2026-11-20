"""Verify that generated OpenAPI describes the registered API routes and models."""

from fastapi.routing import APIRoute

from docextract.api.routes.evidence import router as evidence_router
from docextract.api.routes.extract import router as extract_router
from docextract.api.routes.health import HealthResponse
from docextract.api.routes.health import router as health_router
from docextract.api.routes.validate import router as validate_router
from docextract.main import app
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import EvidenceExtractionResponse
from docextract.schemas_validation import InvoiceValidationResult


def _registered_api_operations() -> dict[str, tuple[set[str], type[object]]]:
    operations: dict[str, tuple[set[str], type[object]]] = {}
    for prefix, router in (
        ("/api", health_router),
        ("/api", extract_router),
        ("/api", evidence_router),
        ("/api", validate_router),
    ):
        for route in router.routes:
            if isinstance(route, APIRoute) and route.response_model is not None:
                operations[f"{prefix}{route.path}"] = (
                    {method.lower() for method in route.methods or set()},
                    route.response_model,
                )
    return operations


def test_openapi_paths_and_methods_match_registered_api_routes() -> None:
    schema = app.openapi()
    registered = _registered_api_operations()
    expected = {
        "/api/health": ({"get"}, HealthResponse),
        "/api/extract": ({"post"}, InvoiceExtractionData),
        "/api/extract/evidence": ({"post"}, EvidenceExtractionResponse),
        "/api/validate": ({"post"}, InvoiceValidationResult),
    }
    assert registered == expected
    documented = {
        path: {
            method: operation
            for method, operation in item.items()
            if method in {"get", "post", "put", "patch", "delete"}
        }
        for path, item in schema["paths"].items()
        if path.startswith("/api/")
    }

    assert {path: methods for path, (methods, _) in registered.items()} == {
        path: set(methods) for path, methods in documented.items()
    }

    for path, (methods, response_model) in registered.items():
        for method in methods:
            operation = documented[path][method]
            assert operation["summary"]
            assert operation["description"]
            ref = operation["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ]
            assert ref.endswith(f"/{response_model.__name__}")


def test_openapi_documents_request_and_response_models_without_auth() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert paths["/api/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/HealthResponse")

    extract = paths["/api/extract"]["post"]
    request_content = extract["requestBody"]["content"]
    assert "multipart/form-data" in request_content
    upload_schema = request_content["multipart/form-data"]["schema"]["$ref"].rsplit(
        "/", maxsplit=1
    )[-1]
    upload_properties = schema["components"]["schemas"][upload_schema]["properties"]
    assert upload_properties["file"]["type"] == "string"
    assert upload_properties["file"]["contentMediaType"] == "application/octet-stream"
    assert extract["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/InvoiceExtractionData")
    assert {"400", "413", "415", "422", "502", "503", "504"} <= set(
        extract["responses"]
    )
    for status in ("400", "413", "415", "422", "502", "503", "504"):
        error_ref = extract["responses"][status]["content"]["application/json"]["schema"][
            "$ref"
        ]
        assert error_ref.endswith("/ApiErrorResponse")

    evidence = paths["/api/extract/evidence"]["post"]
    assert "multipart/form-data" in evidence["requestBody"]["content"]
    assert evidence["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/EvidenceExtractionResponse")

    validation = paths["/api/validate"]["post"]
    invoice_schema = validation["requestBody"]["content"]["application/json"]["schema"]
    assert invoice_schema["$ref"].endswith("/InvoiceExtractionData")
    assert validation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/InvoiceValidationResult")

    for path in paths.values():
        for operation in path.values():
            if isinstance(operation, dict) and "responses" in operation:
                assert "security" not in operation
    assert "security" not in schema
