import logging
from typing import Generator, Type

from . import affinity_base
from ..module_types import affinity_v2_api as affinity_types, base


class AffinityClientV2(affinity_base.AffinityBase):
    __URL = 'https://api.affinity.co/v2/'

    def __init__(self, api_key: str):
        self.__logger = logging.getLogger('AffinityClientV2')
        super().__init__(api_key)

    def __url(self, path: str) -> str:
        return f'{self.__URL}{path}'

    def __handle_bugs(self, response: affinity_types.PaginatedResponse) -> affinity_types.PaginatedResponse:
        if response.data and 'listId' in response.data[0].keys():
            self.__logger.warning('Removing listId from list entries - this is a bug in the V2 API')

            for row in response.data:
                del row['listId']

        return response

    def __get_paginated_results(
            self,
            url: str,
            inner_type: Type[base.BaseSubclass],
            params: dict | None = None,
            extra_attrs: dict | None = None
    ) -> Generator[base.BaseSubclass, None, None]:
        response = self._send_request(
            method='get',
            url=url,
            result_type=affinity_types.PaginatedResponse,
            params=params or {}
        )
        response = self.__handle_bugs(response)

        yield from [inner_type.model_validate(item | (extra_attrs or {})) for item in response.data]

        while response.pagination.next_url is not None:
            response = self._send_request(
                method='get',
                url=response.pagination.next_url,
                result_type=affinity_types.PaginatedResponse
            )
            response = self.__handle_bugs(response)

            yield from [inner_type.model_validate(item | (extra_attrs or {})) for item in response.data]

    def get_companies(self) -> Generator[affinity_types.Company, None, None]:
        self.__logger.info('Getting companies')

        return self.__get_paginated_results(
            url=self.__url('companies'),
            params={'fieldTypes': ['enriched', 'global', 'relationship-intelligence']},
            inner_type=affinity_types.Company
        )

    def get_company_fields(self) -> Generator[affinity_types.FieldMetadata, None, None]:
        self.__logger.info('Getting company fields')

        return self.__get_paginated_results(
            url=self.__url('companies/fields'),
            inner_type=affinity_types.FieldMetadata
        )

    def get_list_metadatas(self) -> Generator[affinity_types.ListMetadata, None, None]:
        self.__logger.info('Getting list metadatas')

        return self.__get_paginated_results(
            url=self.__url('lists'),
            inner_type=affinity_types.ListMetadata
        )

    def get_list_fields(self, list_id: int) -> Generator[affinity_types.ListFieldMetadata, None, None]:
        self.__logger.info(f'Getting fields for list {list_id}')

        return self.__get_paginated_results(
            url=self.__url(f'lists/{list_id}/fields'),
            inner_type=affinity_types.ListFieldMetadata,
            extra_attrs={'list_affinity_id': list_id}
        )

    def get_list_entries(self, list_id: int) -> Generator[affinity_types.ListEntry, None, None]:
        self.__logger.info(f'Getting entries for list {list_id}')

        return self.__get_paginated_results(
            url=self.__url(f'lists/{list_id}/list-entries'),
            params={'fieldTypes': ['enriched', 'global', 'relationship-intelligence', 'list']},
            inner_type=affinity_types.ListEntry,
            extra_attrs={'list_affinity_id': list_id}
        )

    def get_view_metadatas(self, list_id: int) -> Generator[affinity_types.ViewMetadata, None, None]:
        self.__logger.info('Getting view metadatas')

        return self.__get_paginated_results(
            url=self.__url(f'lists/{list_id}/saved-views'),
            inner_type=affinity_types.ViewMetadata,
            extra_attrs={'list_affinity_id': list_id}
        )

    def get_view_entries(self, list_id: int, view_id: int) -> Generator[affinity_types.ViewEntry, None, None]:
        self.__logger.info(f'Getting entries for view {view_id} of list {list_id}')

        return self.__get_paginated_results(
            url=self.__url(f'lists/{list_id}/saved-views/{view_id}/list-entries'),
            params={'fieldTypes': ['enriched', 'global', 'relationship-intelligence', 'list']},
            inner_type=affinity_types.ViewEntry,
            extra_attrs={
                'list_affinity_id': list_id,
                'view_affinity_id': view_id
            }
        )

    def get_people_fields(self) -> Generator[affinity_types.FieldMetadata, None, None]:
        self.__logger.info('Getting people fields')

        return self.__get_paginated_results(
            url=self.__url('persons/fields'),
            inner_type=affinity_types.FieldMetadata
        )

    def get_people(self) -> Generator[affinity_types.Person, None, None]:
        self.__logger.info('Getting people')

        return self.__get_paginated_results(
            url=self.__url('persons'),
            params={'fieldTypes': ['enriched', 'global', 'relationship-intelligence']},
            inner_type=affinity_types.Person
        )

    def get_single_person(self, person_id: int) -> affinity_types.Person:
        self.__logger.info(f'Getting person {person_id}')

        return self._send_request(
            method='get',
            url=self.__url(f'persons/{person_id}'),
            result_type=affinity_types.Person
        )
