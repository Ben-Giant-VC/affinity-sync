import logging

from psycopg import sql

from . import clients
from . import reader
from .module_types import db_types


class ViewBuilder:
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

    def build_list(self, list_id: int):
        self.__logger.info(f'Building view for list {list_id}')
        all_list_fields = self.__reader.get_list_fields(
            only_live=True,
            qualifiers=[db_types.Qualification(field='list_affinity_id', value=list_id, type='equals')]
        )
        list_fields = list({field.name: field for field in all_list_fields}.values())
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

    def build_people(self):
        self.__logger.info('Building person view')
        all_person_fields = self.__reader.get_people_fields(only_live=True)
        person_fields = list({field.name: field for field in all_person_fields}.values())
        view = sql.SQL(
            '''
                WITH expanded AS (
                    SELECT
                        person.id,
                        person.affinity_id,
                        person.first_name,
                        person.last_name,
                        person.primary_email_address,
                        person.email_addresses,
                        person.type,
                        jsonb_array_elements(person.fields) as field
                    FROM affinity.person
                    WHERE person.valid_to IS NULL
                ),
                {ctes}
                {select}
            '''
        ).format(
            ctes=sql.SQL(', ').join(
                [
                    sql.SQL(
                        '''
                            {cte_name} AS (
                                SELECT
                                    expanded.id,
                                    expanded.affinity_id,
                                    expanded.first_name,
                                    expanded.last_name,
                                    expanded.primary_email_address,
                                    expanded.email_addresses,
                                    expanded.type,
                                    field -> 'value' -> 'data' as field_value
                                FROM expanded
                                WHERE expanded.field ->> 'affinity_id' = {field_id}
                            )
                        '''
                    ).format(
                        cte_name=sql.Identifier(field.affinity_id),
                        field_id=sql.Literal(field.affinity_id)
                    )
                    for field in person_fields
                ]
            ),
            select=sql.SQL(
                '''
                    SELECT
                        {first_field}.id,
                        {first_field}.affinity_id,
                        {first_field}.first_name,
                        {first_field}.last_name,
                        {first_field}.primary_email_address,
                        {first_field}.email_addresses,
                        {first_field}.type,
                        {first_field}.field_value as {first_field_name},
                        {other_fields}
                    FROM {first_field}
                    {join}
                '''
            ).format(
                first_field=sql.Identifier(person_fields[0].affinity_id),
                first_field_name=sql.Identifier(person_fields[0].name),
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
                        for field in person_fields[1:]
                    ]
                ),
                join=sql.SQL('\n').join(
                    [
                        sql.SQL('LEFT JOIN {field} ON {first_field}.id = {field}.id').format(
                            field=sql.Identifier(field.affinity_id),
                            first_field=sql.Identifier(person_fields[0].affinity_id)
                        )
                        for field in person_fields[1:]
                    ]
                )
            )
        )

        query = sql.SQL(
            '''
                DROP VIEW IF EXISTS affinity.person_view;
                CREATE VIEW affinity.person_view AS
                {view}
            '''
        ).format(
            view=view
        )

        self.__db_client.execute(query)

        self.__logger.info('Person view built')

    def build_companies(self):
        self.__logger.info('Building company view')
        all_company_fields = self.__reader.get_company_fields(only_live=True)
        company_fields = list({field.name: field for field in all_company_fields}.values())

        view = sql.SQL(
            '''
                WITH expanded AS (
                    SELECT
                        company.id,
                        company.affinity_id,
                        company.name,
                        company.domain,
                        company.domains,
                        company.is_global,
                        jsonb_array_elements(company.fields) as field
                    FROM affinity.company
                    WHERE company.valid_to IS NULL
                ),
                {ctes}
                {select}
            '''
        ).format(
            ctes=sql.SQL(', ').join(
                [
                    sql.SQL(
                        '''
                            {cte_name} AS (
                                SELECT
                                    expanded.id,
                                    expanded.affinity_id,
                                    expanded.name,
                                    expanded.domain,
                                    expanded.domains,
                                    expanded.is_global,
                                    field -> 'value' -> 'data' as field_value
                                FROM expanded
                                WHERE expanded.field ->> 'affinity_id' = {field_id}
                            )
                        '''
                    ).format(
                        cte_name=sql.Identifier(field.affinity_id),
                        field_id=sql.Literal(field.affinity_id)
                    )
                    for field in company_fields
                ]
            ),
            select=sql.SQL(
                '''
                    SELECT
                        {first_field}.id,
                        {first_field}.affinity_id,
                        {first_field}.name,
                        {first_field}.domain,
                        {first_field}.domains,
                        {first_field}.is_global,
                        {first_field}.field_value as {first_field_name},
                        {other_fields}
                    FROM {first_field}
                    {join}
                '''
            ).format(
                first_field=sql.Identifier(company_fields[0].affinity_id),
                first_field_name=sql.Identifier(company_fields[0].name),
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
                        for field in company_fields[1:]
                    ]
                ),
                join=sql.SQL('\n').join(
                    [
                        sql.SQL('LEFT JOIN {field} ON {first_field}.id = {field}.id').format(
                            field=sql.Identifier(field.affinity_id),
                            first_field=sql.Identifier(company_fields[0].affinity_id)
                        )
                        for field in company_fields[1:]
                    ]
                )
            )
        )

        query = sql.SQL(
            '''
                DROP VIEW IF EXISTS affinity.company_view;
                CREATE VIEW affinity.company_view AS
                {view}
            '''
        ).format(
            view=view
        )

        self.__db_client.execute(query)

        self.__logger.info('Person view built')
