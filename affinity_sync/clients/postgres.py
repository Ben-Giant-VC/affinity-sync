import json
import logging
import typing
from typing import Literal, Any, Type

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from ..module_types import base, db_types, affinity_v2_api as affintiy_types
from ..resources import schema

Table = Literal[
    'company',
    'company_field',
    'list_entry',
    'list_field',
    'list_metadata',
    'person',
    'person_field',
    'view_entry',
    'view_metadata'
]

TABLE_TYPES = {
    'company': db_types.Company,
    'company_field': db_types.FieldMetadata,
    'list_entry': db_types.ListEntry,
    'list_field': db_types.ListFieldMetadata,
    'list_metadata': db_types.ListMetadata,
    'person': db_types.Person,
    'person_field': db_types.FieldMetadata,
    'view_entry': db_types.ViewEntry,
    'view_metadata': db_types.ViewMetadata
}

TYPE_MAP = {
    'string': 'TEXT',
    'integer': 'INTEGER',
    'boolean': 'BOOLEAN',
    'object': 'JSONB'
}


class PostgresClient:
    __connection = None

    def __init__(
            self,
            host: str,
            port: int,
            user: str,
            password: str,
            dbname: str
    ):
        self.__host = host
        self.__port = port
        self.__user = user
        self.__password = password
        self.__dbname = dbname

        self.__logger = logging.getLogger('PostgresClient')
        self.__assert_schema_exists()

    def connection(self) -> psycopg.Connection:
        if self.__connection is None or self.__connection.closed:
            self.__connection = psycopg.connect(
                host=self.__host,
                port=self.__port,
                user=self.__user,
                password=self.__password,
                dbname=self.__dbname,
                autocommit=True,
            )

            with self.__connection.cursor() as cursor:
                cursor.execute('SET TIMEZONE TO UTC')
                cursor.execute('SET search_path TO affinity')

        return self.__connection

    def execute(self, query: sql.SQL | sql.Composed):
        with self.connection().cursor() as cursor:
            cursor.execute(query)
            self.connection().commit()

    def fetch(
            self,
            query: sql.SQL | sql.Composed,
            result_type: Type[base.BaseSubclass] | None = None
    ) -> list[base.BaseSubclass | dict]:
        class Wrapper(base.Base):
            payload: result_type

        with self.connection().cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

            if not result_type:
                return results if results else []

            if typing.get_origin(result_type) is typing.Union:
                return [Wrapper(payload=result).payload for result in results]

            return [result_type.model_validate(result) for result in results]

    def __assert_schema_exists(self):
        self.execute(sql.SQL(schema.SCHEMA))

    @staticmethod
    def get_postgres_type(info: dict) -> Literal[
        'TEXT',
        'TEXT[]',
        'INTEGER',
        'INTEGER[]',
        'BOOLEAN',
        'BOOLEAN[]',
        'JSONB',
        'TIMESTAMP'
    ]:

        if info['title'].upper().endswith(' AT'):
            return 'TIMESTAMP'

        if 'anyOf' in info:
            return TYPE_MAP.get(info['anyOf'][0]['type'])

        if info['type'] == 'array':
            item_type = info['items'].get('type')

            if not item_type:
                return 'JSONB'

            converted = TYPE_MAP.get(item_type)

            if converted is None:
                raise ValueError(f'Unsupported type {info}')

            return f'{converted}[]'

        result = TYPE_MAP.get(info['type'])

        if result is None:
            raise ValueError(f'Unsupported type {info}')

        return result

    def __to_db_value(self, type: str, value: Any) -> Any:
        result = value

        if isinstance(value, list):
            result = [self.__to_db_value('DUMMY', item) for item in value]

        if isinstance(value, base.Base):
            result = value.model_dump(by_alias=False)

        if type == 'JSONB':
            result = json.dumps(result)

        return result

    def insert_as_of_relations(self, table: Table, objs: list[base.BaseSubclass]):
        self.__logger.info(f'Inserting {len(objs)} records into {table}')
        object_properties = objs[0].model_json_schema(by_alias=False)['properties']
        query: sql.Composed = sql.SQL(
            '''
                WITH to_insert (
                    {columns}
                ) AS (
                VALUES
                    {values}
                ),
                existing AS (
                    SELECT
                        {table}.id as existing_id,
                        {existing_columns_with_names},
                        {to_insert_columns},
                        NOT (
                        {change_check}
                        ) as has_changed
                    FROM {table}
                    JOIN to_insert ON
                        {table}.affinity_id = to_insert.affinity_id AND
                        {table}.valid_to IS NULL
                ),
                updated_valid_tos AS (
                    UPDATE {table} SET valid_to = NOW()
                    FROM existing
                    WHERE
                        {table}.id = existing.existing_id AND
                        existing.has_changed
                    RETURNING {table}.affinity_id
                ),
                insert_new AS (
                    INSERT INTO {table} (
                        {columns}
                    )
                    SELECT
                        {columns}
                    FROM to_insert
                    WHERE to_insert.affinity_id NOT IN (SELECT affinity_id FROM existing)
                    RETURNING id
                ),
                insert_existing AS (
                    INSERT INTO {table} (
                        {columns}
                    )
                    SELECT
                        {new_column_names}
                    FROM existing
                    WHERE "existing_affinity_id" IN (SELECT affinity_id FROM updated_valid_tos)
                    RETURNING id
                )
                SELECT * FROM insert_existing
                UNION ALL
                SELECT * FROM insert_new
            '''
        ).format(
            columns=sql.SQL(',\n').join(sql.Identifier(column) for column in object_properties.keys()),
            values=sql.SQL(',').join(
                sql.SQL('\n({values})').format(
                    values=sql.SQL(',').join(
                        sql.SQL('{value}::{type}').format(
                            value=sql.Literal(self.__to_db_value(
                                type=self.get_postgres_type(object_properties[column]),
                                value=getattr(obj, column))
                            ),
                            type=sql.SQL(self.get_postgres_type(object_properties[column]))
                        )
                        for column in object_properties.keys()
                    )
                ) for obj in objs
            ),
            table=sql.SQL('affinity.{table}').format(table=sql.Identifier(table)),
            existing_columns_with_names=sql.SQL(',\n').join(
                sql.SQL('{table}.{column} as {column_name}').format(
                    table=sql.Identifier(table),
                    column=sql.Identifier(column),
                    column_name=sql.Identifier(f'existing_{column}')
                ) for column in object_properties.keys()
            ),
            new_column_names=sql.SQL(',\n').join(
                sql.Identifier(f'to_insert_{column}')
                for column in object_properties.keys()
            ),
            to_insert_columns=sql.SQL(',\n').join(
                sql.SQL('to_insert.{column} as {column_name}').format(
                    column=sql.Identifier(column),
                    column_name=sql.Identifier(f'to_insert_{column}')
                ) for column in object_properties.keys()
            ),
            change_check=sql.SQL(' AND\n').join(
                sql.SQL('{table}.{column} = to_insert.{column}').format(
                    table=sql.Identifier(table),
                    column=sql.Identifier(column)
                ) for column in object_properties.keys()
                if column != 'affinity_id'
            )
        )

        self.execute(query)

    def set_dead_as_of_relations(self, table: Table, live_affinity_ids: list[int], qualifier: dict[str, Any] = None):

        if not live_affinity_ids:
            return

        self.__logger.info(f'Setting dead records in {table} (now live: {len(live_affinity_ids)})')
        qualifier = qualifier or {}

        query = sql.SQL(
            '''
                UPDATE affinity.{table}
                SET valid_to = NOW()
                WHERE 
                    affinity_id NOT IN ({live_affinity_ids}) AND 
                    valid_to IS NULL  {qualification}
            '''
        ).format(
            table=sql.Identifier(table),
            live_affinity_ids=sql.SQL(',').join(sql.Literal(affinity_id) for affinity_id in live_affinity_ids),
            qualification=sql.SQL(' AND {extra}' if qualifier else '').format(
                extra=sql.SQL(' AND ').join(
                    sql.SQL('{k} = {v}').format(k=sql.Identifier(k), v=v)
                    for k, v in qualifier.items()
                )
            )
        )

        self.execute(query)

    def fetch_rows(
            self,
            table: Table,
            only_live: bool = True,
            qualifiers: list[db_types.Qualification] = None
    ) -> list[base.BaseSubclass]:
        self.__logger.info(f'Fetching rows from {table}')

        if only_live:
            qualifiers = (qualifiers or []) + [db_types.Qualification(field='valid_to', value=None, type='is')]

        query = sql.SQL(
            '''
                SELECT
                    *
                FROM affinity.{table}
                {where}
            '''
        ).format(
            table=sql.Identifier(table),
            where=sql.SQL('WHERE {conditions}' if qualifiers else '').format(
                conditions=sql.SQL(' AND ').join([qualification.query for qualification in qualifiers])
            )
        )

        return self.fetch(query, TABLE_TYPES[table])

    def fetch_people_ids_by_field(self, field_name: str, field_values: list) -> list[int]:
        query = sql.SQL(
            '''
                SELECT
                    affinity_id
                FROM affinity.person_view
                WHERE {field_name} = ANY(ARRAY[{field_values}])
            '''
        ).format(
            field_name=sql.Identifier(field_name),
            field_values=sql.SQL(',').join(
                sql.SQL(f'\'"{value}"\'::JSONB').format(value=sql.Literal(value))
                for value in field_values
            )
        )

        return [x['affinity_id'] for x in self.fetch(query)]

    def fetch_company_ids_by_field(self, field_name: str, field_values: list) -> list[int]:
        query = sql.SQL(
            '''
                SELECT
                    affinity_id
                FROM affinity.company_view
                WHERE {field_name} = ANY(ARRAY[{field_values}])
            '''
        ).format(
            field_name=sql.Identifier(field_name),
            field_values=sql.SQL(',').join(
                sql.SQL(f'\'"{value}"\'::JSONB').format(value=sql.Literal(value))
                for value in field_values
            )
        )

        return [x['affinity_id'] for x in self.fetch(query)]

    def fetch_syncs(self) -> list[db_types.Sync]:
        self.__logger.info('Fetching syncs')
        return self.fetch(
            sql.SQL(
                '''
                    SELECT 
                        id,
                        type,
                        frequency_minutes,
                        data,
                        live
                    FROM affinity.sync
                '''
            ), db_types.SyncTypes)

    def insert_syncs(self, syncs: list[db_types.Sync]) -> None:

        if not syncs:
            return

        self.__logger.info(f'Inserting {len(syncs)} syncs')
        self.execute(
            sql.SQL(
                '''
                INSERT INTO affinity.sync (
                    type,
                    frequency_minutes,
                    data,
                    live
                )
                VALUES
                    {values}
                '''
            ).format(
                values=sql.SQL(',').join(
                    sql.SQL('({type}, {frequency_minutes}, {data}::JSONB, {live})').format(
                        type=sql.Literal(sync.type),
                        frequency_minutes=sql.Literal(sync.frequency_minutes),
                        data=sql.Literal(json.dumps(sync.data.model_dump(by_alias=False)) if sync.data else None),
                        live=sql.Literal(sync.live)
                    ) for sync in syncs
                )
            )
        )

    def remove_syncs(self, syncs: list[db_types.Sync]) -> None:
        if not syncs:
            return

        if any(sync.id is None for sync in syncs):
            raise ValueError('Cannot remove unsaved syncs')

        self.__logger.info(f'Removing {len(syncs)} syncs')
        self.execute(
            sql.SQL('DELETE FROM affinity.sync WHERE id IN ({ids})').format(
                ids=sql.SQL(',').join(sql.Literal(sync.id) for sync in syncs)
            )
        )

    def update_sync(self, sync: db_types.Sync) -> None:
        self.__logger.info(f'Updating sync {sync.id}')
        self.execute(
            sql.SQL(
                '''
                UPDATE affinity.sync
                SET
                    type = {type},
                    frequency_minutes = {frequency_minutes},
                    data = {data}::JSONB,
                    live = {live}
                WHERE
                    id = {id}
                '''
            ).format(
                type=sql.Literal(sync.type),
                frequency_minutes=sql.Literal(sync.frequency_minutes),
                data=sql.Literal(json.dumps(sync.data.model_dump(by_alias=False)) if sync.data else None),
                live=sql.Literal(sync.live),
                id=sql.Literal(sync.id)
            )
        )

    def fetch_due_syncs(self) -> list[db_types.Sync]:
        self.__logger.info('Fetching due syncs')
        query = sql.SQL(
            '''
                SELECT 
                    sync.id,
                    sync.type,
                    sync.frequency_minutes,
                    sync.data,
                    sync.live
                FROM affinity.sync
                LEFT JOIN LATERAL (
                    SELECT
                        sync_log.id,
                        sync_log.created_at
                    FROM affinity.sync_log
                    WHERE
                        sync_log.sync_id = sync.id
                    ORDER BY
                        sync_log.created_at DESC
                    LIMIT 1
                ) sync_log ON TRUE
                WHERE
                    live = TRUE AND
                    (
                        sync_log.id IS NULL OR
                        sync_log.created_at < NOW() - INTERVAL '1 MINUTE' * frequency_minutes
                    )
            '''
        )

        return self.fetch(query, db_types.SyncTypes)

    def fetch_latest_log_per_sync(self) -> list[db_types.SyncLog]:
        self.__logger.info('Fetching latest log per sync')
        return self.fetch(
            sql.SQL(
                '''
                    SELECT DISTINCT ON (sync_id)
                        sync_id,
                        created_at
                    FROM affinity.sync_log
                    ORDER BY sync_id, created_at DESC
                '''
            ), db_types.SyncLog
        )

    def insert_call_entitlement(self, entitlement: affintiy_types.ApiCallEntitlement) -> None:
        self.__logger.debug(f'Inserting call entitlement - {entitlement.org_remaining} remaining')
        self.execute(
            sql.SQL(
                '''
                INSERT INTO affinity.api_call_entitlement (
                    user_limit,
                    user_remaining,
                    user_reset,
                    org_limit,
                    org_remaining,
                    org_reset
                )
                VALUES
                    ({user_limit}, {user_remaining}, {user_reset}, {org_limit}, {org_remaining}, {org_reset})
                '''
            ).format(
                user_limit=sql.Literal(entitlement.user_limit),
                user_remaining=sql.Literal(entitlement.user_remaining),
                user_reset=sql.Literal(entitlement.user_reset),
                org_limit=sql.Literal(entitlement.org_limit),
                org_remaining=sql.Literal(entitlement.org_remaining),
                org_reset=sql.Literal(entitlement.org_reset)
            )
        )

    def fetch_call_entitlements(self, last_n_days: int = 180) -> list[affintiy_types.ApiCallEntitlement]:
        self.__logger.info('Fetching call entitlements')
        return self.fetch(
            sql.SQL(
                '''
                    SELECT
                        user_limit,
                        user_remaining,
                        user_reset,
                        org_limit,
                        org_remaining,
                        org_reset,
                        inserted_at
                    FROM affinity.api_call_entitlement
                    WHERE
                        inserted_at > NOW() - INTERVAL '{days} days'
                    ORDER BY
                        inserted_at DESC
                '''
            ).format(days=sql.Literal(last_n_days))
            , affintiy_types.ApiCallEntitlement
        )

    def insert_sync_log(self, log: db_types.SyncLog) -> None:
        self.__logger.info(f'Inserting sync log for sync {log.sync_id}')
        self.execute(
            sql.SQL(
                '''
                INSERT INTO affinity.sync_log (
                    sync_id
                )
                VALUES
                    ({sync_id})
                '''
            ).format(
                sync_id=sql.Literal(log.sync_id)
            )
        )

    def fetch_latest_logs(self, limit: int = 10) -> list[db_types.SyncLog]:
        self.__logger.info(f'Fetching latest {limit} logs')
        return self.fetch(
            sql.SQL(
                '''
                    SELECT
                        sync_id,
                        created_at
                    FROM affinity.sync_log
                    ORDER BY created_at DESC
                    LIMIT {limit}
                '''
            ).format(
                limit=sql.Literal(limit)
            ), db_types.SyncLog
        )
