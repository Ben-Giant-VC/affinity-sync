import logging

import clients
from module_types import db_types


class Reader:

    def __init__(self):
        self.__logger = logging.getLogger('Reader')
        self.__postgres_client = clients.PostgresClient()

    def get_people(self, only_live: bool = True) -> list[db_types.Person]:
        return self.__postgres_client.fetch_rows(
            table='person',
            only_live=only_live
        )

    def get_people_fields(self, only_live: bool = True) -> list[db_types.FieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='person_field',
            only_live=only_live
        )

    def get_companies(self, only_live: bool = True) -> list[db_types.Company]:
        return self.__postgres_client.fetch_rows(
            table='company',
            only_live=only_live
        )

    def get_company_fields(self, only_live: bool = True) -> list[db_types.FieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='company_field',
            only_live=only_live
        )

    def get_lists(self, only_live: bool = True) -> list[db_types.ListMetadata]:
        return self.__postgres_client.fetch_rows(
            table='list_metadata',
            only_live=only_live
        )

    def get_list_fields(self, only_live: bool = True) -> list[db_types.ListFieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='list_field',
            only_live=only_live
        )

    def get_list_entries(self, only_live: bool = True, list_id: int = None) -> list[db_types.ListEntry]:
        return self.__postgres_client.fetch_rows(
            table='list_entry',
            only_live=only_live,
            qualifier={'list_affinity_id': list_id} if list_id else None
        )

    def get_views(self, only_live: bool = True, list_id: int = None) -> list[db_types.ViewMetadata]:
        return self.__postgres_client.fetch_rows(
            table='view_metadata',
            only_live=only_live,
            qualifier={'list_affinity_id': list_id} if list_id else None
        )

    def get_view_entries(
            self,
            only_live: bool = True,
            list_id: int = None,
            view_id: int = None
    ) -> list[db_types.ViewEntry]:
        if view_id is not None and list_id is None or view_id is None and list_id is not None:
            raise ValueError('Both list_id and view_id must be specified or neither')

        return self.__postgres_client.fetch_rows(
            table='view_entry',
            only_live=only_live
        )


if __name__ == '__main__':
    reader = Reader()
    entries = reader.get_list_entries(only_live=True, list_id=54119)

    for entry in entries:
        print(entry.entity)
        break
