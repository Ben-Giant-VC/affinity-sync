import datetime
from typing import Any, Literal

import pydantic

from . import base


class ApiCallEntitlement(base.Base, extra='ignore'):
    user_limit: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-User', 'user_limit')
    )
    user_remaining: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-User-Remaining', 'user_remaining')
    )
    user_reset: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-User-Reset', 'user_reset')
    )
    org_limit: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-Org', 'org_limit')
    )
    org_remaining: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-Org-Remaining', 'org_remaining')
    )
    org_reset: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('X-Ratelimit-Limit-Org-Reset', 'org_reset')
    )
    inserted_at: datetime.datetime | None = None


class Pagination(base.Base):
    next_url: str | None = pydantic.Field(validation_alias='nextUrl')
    prev_url: str | None = pydantic.Field(validation_alias='prevUrl')


class PaginatedResponse(base.Base):
    data: list[dict]
    pagination: Pagination


FieldTypes = Literal['enriched', 'global', 'list', 'relationship-intelligence']

FieldValueTypes = Literal[
    'person', 'person-multi', 'company', 'company-multi', 'filterable-text', 'filterable-text-multi', 'number',
    'number-multi', 'datetime', 'location', 'location-multi', 'text', 'ranked-dropdown', 'dropdown', 'dropdown-multi',
    'formula-number', 'interaction'
]


class FieldMetadata(base.Base):
    affinity_id: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    name: str
    type: FieldTypes
    enrichment_source: str | None = pydantic.Field(
        validation_alias=pydantic.AliasChoices('enrichmentSource', 'enrichment_source')
    )
    value_type: FieldValueTypes = pydantic.Field(
        validation_alias=pydantic.AliasChoices('valueType', 'value_type')
    )


class ListFieldMetadata(FieldMetadata):
    list_affinity_id: int


class FieldValue(base.Base):
    type: str
    data: Any


class Field(base.Base):
    affinity_id: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    name: str
    type: str
    enrichment_source: str | None = pydantic.Field(
        validation_alias=pydantic.AliasChoices('enrichmentSource', 'enrichment_source')
    )
    value: FieldValue


class Company(base.Base):
    affinity_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    name: str
    domain: str | None = None
    domains: list[str]
    is_global: bool = pydantic.Field(
        validation_alias=pydantic.AliasChoices('isGlobal', 'is_global')
    )
    fields: list[Field]


class ListMetadata(base.Base):
    affinity_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    name: str
    creator_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('creatorId', 'creator_id')
    )
    owner_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('ownerId', 'owner_id')
    )
    is_public: bool = pydantic.Field(
        validation_alias=pydantic.AliasChoices('isPublic', 'is_public')
    )
    type: str


class Entry(base.Base):
    affinity_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    type: str
    created_at: datetime.datetime = pydantic.Field(
        validation_alias=pydantic.AliasChoices('createdAt', 'created_at')
    )
    creator_id: int | None = pydantic.Field(
        validation_alias=pydantic.AliasChoices('creatorId', 'creator_id')
    )
    entity: dict


class ListEntry(Entry):
    list_affinity_id: int = pydantic.Field(validation_alias=pydantic.AliasChoices('ListId', 'list_affinity_id', ))


class ViewEntry(Entry):
    list_affinity_id: int
    view_affinity_id: int


class ViewMetadata(base.Base):
    list_affinity_id: int
    affinity_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    name: str
    type: str
    created_at: datetime.datetime = pydantic.Field(
        validation_alias=pydantic.AliasChoices('createdAt', 'created_at')
    )


class Person(base.Base):
    affinity_id: int = pydantic.Field(
        validation_alias=pydantic.AliasChoices('id', 'affinity_id')
    )
    first_name: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices('firstName', 'first_name')
    )
    last_name: str | None = pydantic.Field(
        validation_alias=pydantic.AliasChoices('lastName', 'last_name')
    )
    primary_email_address: str | None = pydantic.Field(
        validation_alias=pydantic.AliasChoices('primaryEmailAddress', 'primary_email_address')
    )
    email_addresses: list[str] = pydantic.Field(
        validation_alias=pydantic.AliasChoices('emailAddresses', 'email_addresses')
    )
    type: str
    fields: list[Field] = pydantic.Field(default_factory=list)
