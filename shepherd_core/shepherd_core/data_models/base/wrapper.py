from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import StringConstraints
from typing_extensions import Annotated

SafeStrClone = Annotated[str, StringConstraints(pattern=r"^[ -~]+$")]
# ⤷ copy avoids circular import


class Wrapper(BaseModel):
    """Prototype for enabling one web- & file-interface for
    all models with dynamic typecasting
    """

    datatype: str
    # ⤷ model-name
    comment: Optional[SafeStrClone] = None
    created: Optional[datetime] = None
    # ⤷ Optional metadata
    parameters: dict
    # ⤷ ShpModel
