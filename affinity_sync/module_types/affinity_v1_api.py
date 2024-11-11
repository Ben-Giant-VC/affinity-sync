import abc
import datetime
from typing import Literal, Union

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


class FieldValue(base.Base, frozen=True):
    id: int
    field_id: int
    list_entry_id: int | None
    entity_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    value: int | float | datetime.datetime | str | dict | None
    value_type: int
    entity_type: int


class SuccessResponse(base.Base):
    success: bool


class Location(base.Base):
    street_address: str | None
    city: str | None
    state: str | None
    country: str | None


FieldTypeMap = {
    'person': int,
    'person-multi': list,
    'company': int,
    'company-multi': list,
    'filterable-text': str,
    'filterable-text-multi': list,
    'number': float,
    'number-multi': list,
    'datetime': datetime.datetime,
    'location': Location,
    'location-multi': list,
    'text': str,
    'ranked-dropdown': str,
    'dropdown': str,
    'dropdown-multi': list,
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
    entity: Opportunity | Person | Company

    @property
    def entity_type_name(self) -> Literal['person', 'company', 'opportunity']:

        if isinstance(self.entity, Person):
            return 'person'

        if isinstance(self.entity, Company):
            return 'company'

        if isinstance(self.entity, Opportunity):
            return 'opportunity'

        raise ValueError(f'Unknown entity type: {self.entity}')


class EntityFile(base.Base, extra='ignore'):
    id: int
    name: str
    size: int
    person_id: int | None
    organization_id: int | None
    opportunity_id: int | None
    uploader_id: int
    created_at: datetime.datetime


class EntityFilesResponse(base.Base):
    entity_files: list[EntityFile]
    next_page_token: str | None


class Note(base.Base):
    id: int
    creator_id: int
    person_ids: list[int]
    associated_person_ids: list[int]
    interaction_person_ids: list[int]
    interaction_id: int | None
    interaction_type: str | None
    is_meeting: bool
    mentioned_person_ids: list[int]
    organization_ids: list[int]
    opportunity_ids: list[int]
    parent_id: int | None
    content: str
    type: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class PaginatedResponse(base.Base, abc.ABC):
    next_page_token: str | None

    @abc.abstractmethod
    def get_results(self) -> list[base.Base]:
        pass


class UnknownEmail(base.Base):
    email: str


class EmailInteraction(base.Base):
    id: int
    date: datetime.datetime
    subject: str | None
    type: int
    from_: Person | UnknownEmail = pydantic.Field(alias='from')
    to: list[Person]
    cc: list[Person]
    direction: int


class EmailInteractionQueryResponse(PaginatedResponse):
    emails: list[EmailInteraction]
    next_page_token: str | None

    def get_results(self) -> list[EmailInteraction]:
        return self.emails


class CallOrMeetingInteraction(base.Base):
    id: int
    date: datetime.datetime
    attendees: list[str]
    start_time: datetime.datetime
    end_time: datetime.datetime | None
    updated_at: datetime.datetime | None
    manual_creator_id: int | None
    title: str | None
    type: int
    notes: list[int]
    persons: list[Person]


class CallOrMeetingInteractionQueryResponse(PaginatedResponse):
    events: list[CallOrMeetingInteraction]
    next_page_token: str | None

    def get_results(self) -> list[CallOrMeetingInteraction]:
        return self.events


SampleWebhookType = Literal[
    'sample.webhook'
]

ListWebhookEventType = Literal[
    'list.created',
    'list.updated',
    'list.deleted'
]

ListEntryWebhookEventType = Literal[
    'list_entry.created',
    'list_entry.deleted'
]

NoteWebhookEventType = Literal[
    'note.created',
    'note.updated',
    'note.deleted'
]

FieldWebhookEventType = Literal[
    'field.created',
    'field.updated',
    'field.deleted'
]

FieldValueWebhookEventType = Literal[
    'field_value.created',
    'field_value.updated',
    'field_value.deleted'
]

PersonWebhookEventType = Literal[
    'person.created',
    'person.updated',
    'person.deleted'
]

OrganizationWebhookEventType = Literal[
    'organization.created',
    'organization.updated',
    'organization.deleted',
    'organization.merged'
]

OpportunityWebhookEventType = Literal[
    'opportunity.created',
    'opportunity.updated',
    'opportunity.deleted'
]

EntityFileWebhookEventType = Literal[
    'file.created',
    'file.deleted'
]

ReminderWebhookEventType = Literal[
    'reminder.created',
    'reminder.updated',
    'reminder.deleted'
]

WebhookEventType = Union[
    SampleWebhookType,
    ListWebhookEventType,
    ListEntryWebhookEventType,
    NoteWebhookEventType,
    FieldWebhookEventType,
    FieldValueWebhookEventType,
    PersonWebhookEventType,
    OrganizationWebhookEventType,
    OpportunityWebhookEventType,
    EntityFileWebhookEventType,
    ReminderWebhookEventType
]


class Webhook(base.Base):
    id: int
    webhook_url: str
    subscriptions: list[WebhookEventType]
    created_by: int
    updated_at: datetime.datetime | None
    disabled: bool


class SampleWebhookBody(base.Base):
    test: bool


class WebhookEvent(base.Base):
    type: WebhookEventType
    body: Union[
        SampleWebhookBody,
        Person,
        ListEntry
    ]
    sent_at: int
