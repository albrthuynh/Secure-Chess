from fastapi import HTTPException, Request
from auth.jwt_helpers import decode_token


def get_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise HTTPException(status_code=401, detail="Authorization Header not found")

    parts = auth_header.split(" ", 1)

    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    jwt = parts[1].strip()
    if not jwt:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    decoded_token = decode_token(jwt, token_type="access")
    sub = decoded_token.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="user_id not found")

    return sub
