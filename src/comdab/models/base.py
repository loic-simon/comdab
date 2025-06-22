from pydantic import BaseModel


class ComdabModel(BaseModel, frozen=True):
    """The base class of all comdab models."""
