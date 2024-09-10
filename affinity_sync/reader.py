import logging
from typing import Any

from . import clients
from .module_types import db_types


class Reader:

    def __init__(
            self,
            db_host: str,
            db_port: int,
            db_name: str,
            db_user: str,
            db_password: str,
    ):
        self.__logger = logging.getLogger('Reader')
        self.__postgres_client = clients.PostgresClient(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
        )

    def get_people(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.Person]:
        return self.__postgres_client.fetch_rows(
            table='person',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_people_ids_by_field(self, field_name: str, field_values: Any) -> list[int]:
        return self.__postgres_client.fetch_people_ids_by_field(field_name=field_name, field_values=field_values)

    def get_company_ids_by_field(self, field_name: str, field_values: list) -> list[int]:
        return self.__postgres_client.fetch_company_ids_by_field(field_name=field_name, field_values=field_values)

    def get_people_fields(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.FieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='person_field',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_companies(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.Company]:
        return self.__postgres_client.fetch_rows(
            table='company',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_company_fields(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.FieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='company_field',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_lists(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ListMetadata]:
        return self.__postgres_client.fetch_rows(
            table='list_metadata',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_list_fields(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ListFieldMetadata]:
        return self.__postgres_client.fetch_rows(
            table='list_field',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_list_metadata(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ListMetadata]:
        return self.__postgres_client.fetch_rows(
            table='list_metadata',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_list_entries(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ListEntry]:
        return self.__postgres_client.fetch_rows(
            table='list_entry',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_views(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ViewMetadata]:
        return self.__postgres_client.fetch_rows(
            table='view_metadata',
            only_live=only_live,
            qualifiers=qualifiers
        )

    def get_view_entries(
            self,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[db_types.ViewEntry]:
        return self.__postgres_client.fetch_rows(
            table='view_entry',
            only_live=only_live,
            qualifiers=qualifiers
        )
