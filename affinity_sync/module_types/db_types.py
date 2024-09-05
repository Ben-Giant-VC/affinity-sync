import datetime
import typing

from module_types import affinity_v2_api, base


class FieldMetadata(affinity_v2_api.FieldMetadata):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class ListFieldMetadata(affinity_v2_api.ListFieldMetadata):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class Company(affinity_v2_api.Company):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class ListMetadata(affinity_v2_api.ListMetadata):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class ListEntry(affinity_v2_api.ListEntry):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None

    @property
    def entity_id(self) -> int:
        return self.entity['id']


class ViewEntry(affinity_v2_api.ViewEntry):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class ViewMetadata(affinity_v2_api.ViewMetadata):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


class Person(affinity_v2_api.Person):
    id: int
    affinity_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None


DBType = typing.Union[
    FieldMetadata,
    ListFieldMetadata,
    Company,
    ListMetadata,
    ListEntry,
    ViewEntry,
    ViewMetadata,
    Person
]

SyncType = typing.Literal['person', 'company', 'list', 'view']


class Sync(base.Base):
    id: int | None = None
    type: SyncType
    frequency_minutes: int = 10080
    live: bool = True
    data: typing.Any


class PersonSync(Sync):
    type: typing.Literal['person'] = 'person'
    data: None = None


class CompanySync(Sync):
    type: typing.Literal['company'] = 'company'
    data: None = None


class ListData(base.Base):
    affinity_list_id: int
    ignore_views: bool = True


class ListSync(Sync):
    type: typing.Literal['list'] = 'list'
    data: ListData


class ViewData(base.Base):
    affinity_list_id: int
    affinity_view_id: int


class ViewSync(Sync):
    type: typing.Literal['view'] = 'view'
    data: ViewData
    live: bool = False


SyncTypes = typing.Union[
    PersonSync,
    CompanySync,
    ListSync,
    ViewSync
]


class SyncLog(base.Base):
    sync_id: int
    created_at: datetime.datetime | None = None
