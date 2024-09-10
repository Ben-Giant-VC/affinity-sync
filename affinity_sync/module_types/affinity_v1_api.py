import datetime
from typing import Any

import pydantic

from ..module_types import base


class AlreadyExists(Exception):
    pass


class MultipleResults(Exception):
    pass


class NewPerson(base.Base):
    first_name: str = pydantic.Field(min_length=1)
    last_name: str = pydantic.Field(min_length=1)
    emails: list[str]
    organization_ids: list[int]

    @pydantic.field_validator('emails')
    def validate_emails(cls, emails):
        return [email.strip() for email in emails if email.strip()]


class Person(base.Base):
    id: int
    type: int
    first_name: str
    last_name: str
    primary_email: str | None
    emails: list[str]
    organization_ids: list[int] = pydantic.Field(default_factory=list)
    list_entries: list = pydantic.Field(default_factory=list)


class PersonQueryResponse(base.Base):
    persons: list[Person]
    next_page_token: str | None


class NewOrganisation(base.Base):
    name: str
    domain: str
    person_ids: list[int]


class DropDownOption(base.Base):
    id: int
    text: str
    rank: int
    color: int


class Field(base.Base):
    id: int
    name: str
    list_id: int | None
    enrichment_source: str
    value_type: int
    allows_multiple: bool
    track_changes: bool
    dropdown_options: list[DropDownOption]


class FieldValue(base.Base):
    id: int
    field_id: int
    list_entry_id: int | None
    entity_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    value: Any
    value_type: int
    entity_type: int


class DeleteResponse(base.Base):
    success: bool


class Location(base.Base):
    street_address: str
    city: str
    state: str
    country: str


FieldTypeMap = {
    'person': int,
    'person-multi': list[int],
    'company': int,
    'company-multi': list[int],
    'filterable-text': str,
    'filterable-text-multi': list[str],
    'number': float,
    'number-multi': list[float],
    'datetime': datetime.datetime,
    'location': Location,
    'location-multi': list[Location],
    'text': str,
    'ranked-dropdown': str,
    'dropdown': str,
    'dropdown-multi': list[str],
}


class Company(base.Base):
    id: int
    name: str
    domain: str | None
    domains: list[str]
    global_: bool = pydantic.Field(alias='global')
    crunchbase_uuid: str | None
    person_ids: list[int] = pydantic.Field(default_factory=list)
    list_entries: list = pydantic.Field(default_factory=list)


class CompanyQueryResponse(base.Base):
    organizations: list[Company]
    next_page_token: str | None


class NewCompany(base.Base):
    name: str
    domain: str | None
    person_ids: list[int]


class OpportunityListEntry(base.Base):
    id: int
    creator_id: int
    list_id: int
    entity_id: int
    entity_type: int
    created_at: datetime.datetime


class Opportunity(base.Base):
    id: int
    name: str
    person_ids: list[int]
    organization_ids: list[int]
    list_entries: list[OpportunityListEntry]

    @property
    def list_id(self) -> int:
        return self.list_entries[0].list_id

    @property
    def list_entry_id(self) -> int:
        return self.list_entries[0].id


class OpportunityQueryResponse(base.Base):
    opportunities: list[Opportunity]
    next_page_token: str | None


class NewOpportunity(base.Base):
    name: str
    list_id: int
    person_ids: list[int] = pydantic.Field(default_factory=list)
    organization_ids: list[int] = pydantic.Field(default_factory=list)


class ListEntry(base.Base):
    id: int
    list_id: int
    creator_id: int
    entity_id: int
    created_at: datetime.datetime
    entity_type: int | None = None
    entity: Person | Company | Opportunity
