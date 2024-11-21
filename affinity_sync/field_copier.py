import functools
import logging

from . import clients
from .module_types import affinity_v1_api as affinity_types


class FieldCopier:
    __logger = logging.getLogger('FieldCopier')

    def __init__(
            self,
            new_entry: affinity_types.ListEntry,
            possible_source_list_ids: list[int],
            api_key: str,
            ignored_field_names: list[str] = None
    ):
        self.__new_entry = new_entry
        self.__source_list_ids = possible_source_list_ids
        self.__client = clients.AffinityClientV1(api_key=api_key)
        self.__ignored_field_names = [field.upper() for field in ignored_field_names] or []

    @functools.cached_property
    def source_entry(self) -> affinity_types.ListEntry | None:

        for list_id in self.__source_list_ids:
            entries = self.__client.fetch_all_list_entries(list_id)
            matched_entry = next((entry for entry in entries if entry.entity_id == self.__new_entry.entity_id), None)

            if matched_entry is not None:
                self.__logger.info(f'Found source entry in list {list_id}')
                return matched_entry

        self.__logger.info('No source entry found')
        return None

    def copy_fields(self):

        if not self.source_entry:
            self.__logger.info('Not copying fields - no source entry found')
            return

        source_field_values = {
            field_value.field_id: field_value for field_value in self.__client.fetch_field_values(
                entity_id=self.source_entry.entity_id,
                entity_type=self.source_entry.entity_type_name,
                list_entry_id=self.source_entry.id
            )
        }
        all_fields = self.__client.fetch_fields()
        source_fields = {
            field.id: field for field in all_fields
            if field.list_id == self.source_entry.list_id
        }
        destination_fields = {
            field.name.upper(): field for field in all_fields
            if field.list_id == self.__new_entry.list_id
        }

        for field_id, field_value in source_field_values.items():
            source_field = source_fields[field_id]
            destination_field = destination_fields.get(source_field.name.upper())

            if destination_field is None:
                self.__logger.info(f'Field {source_field.name} not found in destination list')
                continue

            if destination_field.name.upper() in self.__ignored_field_names:
                self.__logger.info(f'Ignoring field {destination_field.name}')
                continue

            if destination_field is None:
                self.__logger.info(f'Field {source_field.name} not found in destination list')
                continue

            self.__logger.info(f'Copying field {field_value.value} to {destination_field.name}')
            self.__client.create_field_value(
                field_id=destination_field.id,
                entity_id=self.__new_entry.entity_id,
                value=field_value.value,
                list_entry_id=self.__new_entry.id
            )
