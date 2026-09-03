from pydantic import BaseModel


class PromptDefinition(BaseModel):
    name: str
    version: str
    template: str
    description: str
