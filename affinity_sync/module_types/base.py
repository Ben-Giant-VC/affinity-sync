from typing import TypeVar

import pydantic


class Base(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        extra='forbid'
    )


BaseSubclass = TypeVar("BaseSubclass", bound=Base)
