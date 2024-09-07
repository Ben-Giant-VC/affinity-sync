import logging

from psycopg import sql

from . import clients
from . import reader
from .module_types import db_types


class ListViewBuilder:
    __logger = logging.getLogger('ListViewBuilder')

    def __init__(self, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str):
        self.__reader = reader.Reader(
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        )
        self.__db_client = clients.PostgresClient(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )

    def build(self, list_id: int):
        self.__logger.info(f'Building view for list {list_id}')
        list_fields = self.__reader.get_list_fields(
            only_live=True,
            qualifiers=[db_types.Qualification(field='list_affinity_id', value=list_id, type='equals')]
        )
        list_metadata = self.__reader.get_list_metadata(
            only_live=True,
            qualifiers=[db_types.Qualification(field='affinity_id', value=list_id, type='equals')]
        )

        view = sql.SQL(
            '''
                WITH expanded AS (
                    SELECT
                        list_entry.id,
                        list_entry.affinity_id as list_entry_id,
                        entity ->> 'id' as entity_id,
                        entity ->> 'name' as entity_name,
                        entity ->> 'fields' as entity_type,
                        jsonb_array_elements(entity -> 'fields') as field
                    FROM affinity.list_entry
                    WHERE list_entry.valid_to IS NULL AND list_entry.list_affinity_id = {list_id}
                ),
                {ctes}
                {select}
            '''
        ).format(
            list_id=sql.Literal(list_id),
            ctes=sql.SQL(', ').join(
                [
                    sql.SQL(
                        '''
                            {cte_name} AS (
                                SELECT
                                    expanded.id,
                                    expanded.list_entry_id,
                                    expanded.entity_id,
                                    expanded.entity_name,
                                    field -> 'value' -> 'data' as field_value
                                FROM expanded
                                WHERE expanded.field ->> 'id' = {field_id}
                            )
                        '''
                    ).format(
                        cte_name=sql.Identifier(field.affinity_id),
                        field_id=sql.Literal(field.affinity_id)
                    )
                    for field in list_fields
                ]
            ),
            select=sql.SQL(
                '''
                    SELECT
                        {first_field}.id,
                        {first_field}.list_entry_id,
                        {first_field}.entity_id,
                        {first_field}.entity_name,
                        {first_field}.field_value as {first_field_name},
                        {other_fields}
                    FROM {first_field}
                    {join}
                '''
            ).format(
                first_field=sql.Identifier(list_fields[0].affinity_id),
                first_field_name=sql.Identifier(list_fields[0].name),
                second_field=sql.Identifier(list_fields[1].affinity_id),
                other_fields=sql.SQL(', ').join(
                    [
                        sql.SQL(
                            '''
                                {field}.field_value as {field_name}
                            '''
                        ).format(
                            field=sql.Identifier(field.affinity_id),
                            field_name=sql.Identifier(field.name)
                        )
                        for field in list_fields[1:]
                    ]
                ),
                join=sql.SQL('\n').join(
                    [
                        sql.SQL('LEFT JOIN {field} ON {first_field}.id = {field}.id').format(
                            field=sql.Identifier(field.affinity_id),
                            first_field=sql.Identifier(list_fields[0].affinity_id)
                        )
                        for field in list_fields[1:]
                    ]
                )
            )
        )

        query = sql.SQL(
            '''
                DROP VIEW IF EXISTS affinity.{view_name};
                CREATE VIEW affinity.{view_name} AS
                {view}
            '''
        ).format(
            view_name=sql.Identifier(list_metadata[0].name),
            view=view
        )

        self.__db_client.execute(query)
