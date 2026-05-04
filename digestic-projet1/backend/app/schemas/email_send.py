from pydantic import BaseModel, Field


class SendTransactionalEmailBody(BaseModel):
    """Corps optionnel pour POST send-email : si l'un des champs est renseigné, les deux sont requis."""

    subject: str | None = Field(default=None, description="Objet tel qu'envoyé")
    body_html: str | None = Field(default=None, description="Corps HTML tel qu'envoyé")
