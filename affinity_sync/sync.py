import functools
import itertools
import logging
from typing import Generator

from . import clients
from . import view_builder
from .module_types import base, db_types


def insert_entitlement_after(func):
    @functools.wraps(func)
    def wrapper(self: 'Sync', *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.insert_call_entitlement()
        return result

    return wrapper


class Sync:

    def __init__(
            self,
            affinity_api_key: str,
            db_host: str,
            db_port: int,
            db_name: str,
            db_user: str,
            db_password: str,
    ):
        self.__affinity_client = clients.AffinityClientV2(api_key=affinity_api_key)
        self.__postgres_client = clients.PostgresClient(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
        )
        self.__view_builder = view_builder.ViewBuilder(
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        )
        self.__logger = logging.getLogger('Sync')

    def __sync(
            self,
            generator: Generator[base.Base, None, None],
            table_name: clients.PostgresTable,
            qualifier: dict | None = None
    ) -> None:
        all_ids = []

        for chunk in itertools.batched(generator, 100):
            self.__postgres_client.insert_as_of_relations(table_name, chunk)
            all_ids.extend([item.affinity_id for item in chunk])

        self.__postgres_client.set_dead_as_of_relations(
            table=table_name,
            live_affinity_ids=all_ids,
            qualifier=qualifier
        )

    def insert_call_entitlement(self):
        if self.__affinity_client.api_call_entitlement:
            self.__postgres_client.insert_call_entitlement(entitlement=self.__affinity_client.api_call_entitlement)

    @insert_entitlement_after
    def __sync_people(self) -> None:
        self.__sync(self.__affinity_client.get_people_fields(), 'person_field')
        self.__sync(self.__affinity_client.get_people(), 'person')
        self.__view_builder.build_people()

    @insert_entitlement_after
    def __sync_companies(self) -> None:
        self.__sync(self.__affinity_client.get_company_fields(), 'company_field')
        self.__sync(self.__affinity_client.get_companies(), 'company')
        self.__view_builder.build_companies()

    @insert_entitlement_after
    def __sync_list_metadata(self) -> None:
        self.__sync(self.__affinity_client.get_list_metadatas(), 'list_metadata')

    @insert_entitlement_after
    def __sync_list_view_metadata(self, list_id: int) -> None:
        self.__sync(
            generator=self.__affinity_client.get_view_metadatas(list_id),
            table_name='view_metadata',
            qualifier={'list_affinity_id': list_id}
        )

    @insert_entitlement_after
    def __set_up_people_and_company_syncs(self):
        syncs = self.__postgres_client.fetch_syncs()
        people_sync = next((sync for sync in syncs if isinstance(sync, db_types.PersonSync)), None)
        company_sync = next((sync for sync in syncs if isinstance(sync, db_types.CompanySync)), None)

        new_syncs = []

        if not people_sync:
            new_syncs.append(db_types.PersonSync())

        if not company_sync:
            new_syncs.append(db_types.CompanySync())

        self.__postgres_client.insert_syncs(new_syncs)

    @insert_entitlement_after
    def __set_up_list_syncs(self):
        self.__sync_list_metadata()
        list_syncs = [sync for sync in self.__postgres_client.fetch_syncs() if isinstance(sync, db_types.ListSync)]
        list_metas = self.__postgres_client.fetch_rows(table='list_metadata')

        new_syncs = []

        for list_meta in list_metas:
            list_sync = next(
                (
                    sync
                    for sync in list_syncs
                    if sync.data.affinity_list_id == list_meta.affinity_id
                ),
                None
            )

            if not list_sync:
                new_syncs.append(db_types.ListSync(data=db_types.ListData(affinity_list_id=list_meta.affinity_id)))

        self.__postgres_client.insert_syncs(new_syncs)

        syncs_to_remove = []

        live_list_ids = [list_meta.affinity_id for list_meta in list_metas]

        for sync in list_syncs:
            if isinstance(sync, db_types.ListSync) and sync.data.affinity_list_id not in live_list_ids:
                syncs_to_remove.append(sync)

        self.__postgres_client.remove_syncs(syncs_to_remove)

    @insert_entitlement_after
    def __set_up_view_syncs(self):
        all_syncs = self.__postgres_client.fetch_syncs()
        list_syncs = [sync for sync in all_syncs if isinstance(sync, db_types.ListSync)]

        current_view_syncs = [
            (sync.data.affinity_view_id, sync.data.affinity_list_id)
            for sync in all_syncs
            if isinstance(sync, db_types.ViewSync)
        ]
        required_view_syncs = []

        for list_sync in list_syncs:

            if not list_sync.data.ignore_views:
                self.__sync_list_view_metadata(list_sync.data.affinity_list_id)
                views = self.__postgres_client.fetch_rows(
                    table='view_metadata',
                    qualifiers=[db_types.Qualification(
                        field='list_affinity_id',
                        value=list_sync.data.affinity_list_id,
                        type='equals'
                    )]
                )
                required_view_syncs.extend([(view.affinity_id, list_sync.data.affinity_list_id) for view in views])

        new_syncs = [
            db_types.ViewSync(data=db_types.ViewData(affinity_view_id=view_id, affinity_list_id=list_id))
            for view_id, list_id in required_view_syncs
            if (view_id, list_id) not in current_view_syncs
        ]
        extra_syncs = [
            sync for sync in all_syncs
            if isinstance(sync, db_types.ViewSync) and
               (sync.data.affinity_view_id, sync.data.affinity_list_id) not in required_view_syncs
        ]

        self.__postgres_client.insert_syncs(new_syncs)
        self.__postgres_client.remove_syncs(extra_syncs)

    @insert_entitlement_after
    def set_up_syncs(self) -> None:
        self.__set_up_people_and_company_syncs()
        self.__set_up_list_syncs()
        self.__set_up_view_syncs()

    @insert_entitlement_after
    def __sync_list(self, list_id: int) -> None:
        self.__sync(
            generator=self.__affinity_client.get_list_fields(list_id),
            table_name='list_field',
            qualifier={'list_affinity_id': list_id}
        )
        self.__sync(
            generator=self.__affinity_client.get_list_entries(list_id),
            table_name='list_entry',
            qualifier={'list_affinity_id': list_id}
        )
        self.__view_builder.build_list(list_id)

    @insert_entitlement_after
    def __sync_view(self, list_id: int, view_id: int) -> None:
        self.__sync(
            generator=self.__affinity_client.get_view_entries(list_id, view_id),
            table_name='view_entry',
            qualifier={'list_affinity_id': list_id, 'view_affinity_id': view_id}
        )

    def __do_sync(self, sync: db_types.Sync):
        if isinstance(sync, db_types.PersonSync):
            self.__sync_people()

        elif isinstance(sync, db_types.CompanySync):
            self.__sync_companies()

        elif isinstance(sync, db_types.ListSync):
            self.__sync_list(sync.data.affinity_list_id)

        elif isinstance(sync, db_types.ViewSync):
            self.__sync_view(sync.data.affinity_list_id, sync.data.affinity_view_id)

        self.__postgres_client.insert_sync_log(db_types.SyncLog(sync_id=sync.id))

    def run(self):
        self.set_up_syncs()

        for sync in self.__postgres_client.fetch_due_syncs():
            self.__do_sync(sync)
