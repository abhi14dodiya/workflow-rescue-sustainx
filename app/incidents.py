"""Validated, editable synthetic incidents; no imported record grants real authority."""
from pydantic import BaseModel, ConfigDict, Field


class IncidentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    customer_note: str = Field(default='Keep the original items and price. A delay of up to two days is approved. Do not charge again.', min_length=1, max_length=1000)
    available: int = Field(default=2, ge=0, le=100)
    incoming_available: int = Field(default=10, ge=0, le=100)
    alternative_available: int = Field(default=6, ge=0, le=100)
    incoming_days: int = Field(default=1, ge=0, le=30)
    max_delay_days: int = Field(default=2, ge=0, le=30)
    allow_delay: bool = True
    allow_substitution: bool = False
    cancel_requested: bool = False
    payment_unknown: bool = False
    shipped: bool = False
    race: bool = True

    def fixture(self):
        return {
            'id':'custom', 'name':'Your custom recovery incident', 'tag':'Editable incident lab',
            'customer':'Demo Customer', 'company':'Synthetic operations workspace',
            'summary':'A fresh simulation built from your evidence settings and explicit permissions.',
            'message':self.customer_note,
            'policy':{key:getattr(self, key) for key in ('allow_delay', 'max_delay_days', 'allow_substitution', 'cancel_requested')},
            **{key:getattr(self, key) for key in ('available', 'incoming_available', 'alternative_available', 'incoming_days', 'payment_unknown', 'shipped', 'race')},
        }

    def public(self):
        fixture = self.fixture()
        return {key:fixture[key] for key in ('id', 'name', 'tag', 'customer', 'company', 'summary', 'message', 'policy')}
