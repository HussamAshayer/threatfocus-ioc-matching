from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.normalization import InvalidIndicatorError

ERROR_CODES = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    def handle_http_error(request: Request, exc: HTTPException):
        code = ERROR_CODES.get(exc.status_code, "error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "Request body is invalid", details
        )

    @app.exception_handler(InvalidIndicatorError)
    def handle_invalid_indicator(request: Request, exc: InvalidIndicatorError):
        return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_indicator", str(exc))
