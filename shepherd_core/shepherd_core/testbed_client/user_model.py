import secrets
from hashlib import pbkdf2_hmac
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import SecretBytes
from pydantic import SecretStr
from pydantic import constr
from pydantic import root_validator
from pydantic import validate_arguments

from ..data_models.base.content import IdInt
from ..data_models.base.content import NameStr
from ..data_models.base.content import SafeStr
from ..data_models.base.content import id_default
from ..data_models.base.shepherd import ShpModel


@validate_arguments
def hash_password(pw: constr(min_length=20, max_length=100)) -> bytes:
    # TODO: add salt of testbed -> this fn should be part of Testbed-Object
    return pbkdf2_hmac(
        "sha512",
        password=pw.encode("utf-8"),
        salt=b"testbed_salt_TODO",
        iterations=1_000_000,
        dklen=128,
    )


class User(ShpModel):
    """meta-data representation of a testbed-component (physical object)"""

    id: IdInt = Field(  # noqa: A003
        description="Unique ID",
        default_factory=id_default,
    )
    name: NameStr
    description: Optional[SafeStr] = None
    comment: Optional[SafeStr] = None

    name_full: Optional[NameStr] = None
    group: NameStr
    email: EmailStr

    pw_hash: SecretBytes = hash_password("this_will_become_a_salted_slow_hash")
    # ⤷ TODO (min_length=128, max_length=512)

    token: SecretStr
    # ⤷ TODO (min_length=128), request with: token.get_secret_value()

    @root_validator(pre=True)
    def query_database(cls, values: dict) -> dict:
        # TODO:
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        if values.get("token") is None:
            values["token"] = "shepherd_token_" + secrets.token_urlsafe(nbytes=128)
        return values
