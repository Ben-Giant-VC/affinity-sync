import datetime
import logging
from typing import Literal, Union

import requests

from . import affinity_base
from ..module_types import affinity_v1_api as affinity_types


class AffinityClientV1(affinity_base.AffinityBase):
    __URL = 'https://api.affinity.co/'

    def __init__(self, api_key: str):
        self.__logger = logging.getLogger('affinity_sync.AffinityClientV1')
        super().__init__(api_key)

    def __url(self, path: str) -> str:
        return f'{self.__URL}{path}'

    def create_person(self, new_person: affinity_types.NewPerson) -> affinity_types.Person:
        self.__logger.info(f'Creating person - {new_person.first_name} {new_person.last_name}')

        try:
            return self._send_request(
                method='post',
                url=self.__url('persons'),
                result_type=affinity_types.Person,
                json=new_person.model_dump()
            )

        except requests.exceptions.HTTPError as e:

            if e.response.status_code == 422:
                raise affinity_types.AlreadyExists(
                    f'Person already exists - {new_person.first_name} {new_person.last_name}'
                ) from e

            raise e

    def find_person_by_email(self, email: str) -> affinity_types.Person | None:
        self.__logger.debug(f'Finding person by email - {email}')
        response = self._send_request(
            method='get',
            url=self.__url(f'persons'),
            result_type=affinity_types.PersonQueryResponse,
            params={'term': email}
        )

        if response.persons:
            return response.persons[0]

        return None

    def find_person_by_emails(self, emails: list[str]) -> affinity_types.Person | None:
        self.__logger.debug(f'Finding person by emails - {emails}')

        for email in emails:
            person = self.find_person_by_email(email=email)

            if person:
                return person

        return None

    def find_person_by_name(
            self,
            first_name: str,
            last_name: str,
            take_best_match: bool = False
    ) -> affinity_types.Person | None:
        self.__logger.debug(f'Finding person by name - {first_name} {last_name}')
        response = self._send_request(
            method='get',
            url=self.__url(f'persons'),
            result_type=affinity_types.PersonQueryResponse,
            params={'term': f'{first_name} {last_name}'}
        )

        valid_persons = [
            person
            for person in response.persons
            if person.first_name.upper() == first_name.upper() and person.last_name.upper() == last_name.upper()
        ]

        if len(valid_persons) == 1:
            return response.persons[0]

        if len(valid_persons) > 1 and take_best_match:
            return valid_persons[0]

        if len(valid_persons) > 1:
            raise affinity_types.MultipleResults(f'Multiple results found for {first_name} {last_name}')

        return None

    def fetch_fields(self) -> list[affinity_types.Field]:
        self.__logger.debug('Fetching fields')
        return self._send_request(
            method='get',
            url=self.__url('fields'),
            result_type=list[affinity_types.Field]
        )

    def fetch_field_values(
            self,
            entity_id: int,
            entity_type: Literal['person', 'company', 'opportunity'],
            list_entry_id: int | None = None,
    ) -> list[affinity_types.FieldValue]:
        self.__logger.info(
            f'Fetching field values - entity_id={entity_id}, entity_type={entity_type}, list_entry_id={list_entry_id}'
        )
        return self._send_request(
            method='get',
            url=self.__url('field-values'),
            params={
                'person_id': entity_id if entity_type == 'person' and not list_entry_id else None,
                'organization_id': entity_id if entity_type == 'company' and not list_entry_id else None,
                'opportunity_id': entity_id if entity_type == 'opportunity' and not list_entry_id else None,
                'list_entry_id': list_entry_id if list_entry_id else None
            },
            result_type=list[affinity_types.FieldValue]
        )

    def create_field_value(
            self,
            field_id: int,
            entity_id: int,
            value: str,
            list_entry_id: int | None = None
    ) -> affinity_types.FieldValue:
        self.__logger.info(f'Creating field value - {field_id} - {entity_id} - {value}')
        return self._send_request(
            method='post',
            url=self.__url('field-values'),
            json={
                'field_id': field_id,
                'entity_id': entity_id,
                'value': value,
                'list_entry_id': list_entry_id
            },
            result_type=affinity_types.FieldValue
        )

    def update_field_value(self, field_value_id: int, new_value: str) -> None:
        self.__logger.info(f'Updating field value - {field_value_id}')
        self._send_request(
            method='patch',
            url=self.__url(f'field-values/{field_value_id}'),
            json={'value': new_value}
        )

    def delete_field_value(self, field_value_id: int) -> None:
        self.__logger.info(f'Deleting field value - {field_value_id}')
        self._send_request(
            method='delete',
            url=self.__url(f'field-values/{field_value_id}'),
            result_type=affinity_types.SuccessResponse
        )

    def find_company_by_id(self, company_id: int) -> affinity_types.Company | None:
        self.__logger.debug(f'Finding company by id - {company_id}')
        return self._send_request(
            method='get',
            url=self.__url(f'organizations/{company_id}'),
            result_type=affinity_types.Company
        )

    def find_person_by_id(self, person_id: int) -> affinity_types.Person | None:
        self.__logger.debug(f'Finding person by id - {person_id}')
        return self._send_request(
            method='get',
            url=self.__url(f'persons/{person_id}'),
            result_type=affinity_types.Person
        )

    def find_company_by_domain(self, domain: str, take_best_match: bool = False) -> affinity_types.Company | None:
        self.__logger.debug(f'Finding company by domain - {domain}')
        response = self._send_request(
            method='get',
            url=self.__url('organizations'),
            result_type=affinity_types.CompanyQueryResponse,
            params={'term': domain}
        )

        valid_companies = [
            company
            for company in response.organizations
            if any(company_domain.lower() == domain.lower() for company_domain in company.domains)
        ]

        if len(valid_companies) == 1 or (take_best_match and len(valid_companies) > 0):
            return valid_companies[0]

        if len(valid_companies) > 1:
            self.__logger.error(f'Multiple results found for {domain}')
            self.__logger.error(response.organizations)

            raise affinity_types.MultipleResults(f'Multiple results found for {domain}')

        return None

    def find_company_by_domains(self, domains: list[str]) -> affinity_types.Company | None:
        self.__logger.info(f'Finding company by domains - {domains}')

        for domain in domains:
            company = self.find_company_by_domain(domain=domain)

            if company:
                return company

        return None

    def find_company_by_name(self, name: str, take_best_match: bool = False) -> affinity_types.Company | None:
        self.__logger.info(f'Finding company by name - {name}')
        response = self._send_request(
            method='get',
            url=self.__url('organizations'),
            result_type=affinity_types.CompanyQueryResponse,
            params={'term': name}
        )

        valid_companies = [
            company
            for company in response.organizations
            if company.name.upper() == name.upper()
        ]

        if len(valid_companies) == 1 or (take_best_match and len(valid_companies) > 0):
            return valid_companies[0]

        if len(valid_companies) > 1:
            self.__logger.error(f'Multiple results found for {name}')
            self.__logger.error(response.organizations)

            raise affinity_types.MultipleResults(f'Multiple results found for {name}')

        return None

    def create_company(self, new_company: affinity_types.NewCompany) -> affinity_types.Company:
        self.__logger.info(f'Creating company - {new_company.name}')
        return self._send_request(
            method='post',
            url=self.__url('organizations'),
            result_type=affinity_types.Company,
            json=new_company.model_dump()
        )

    def find_opportunity_by_name(self, list_id: int, name: str) -> affinity_types.Opportunity | None:
        self.__logger.debug(f'Finding opportunity by name - {name}')
        response = self._send_request(
            method='get',
            url=self.__url('opportunities'),
            result_type=affinity_types.OpportunityQueryResponse,
            params={'term': name}
        )

        valid_opportunities = [
            opportunity
            for opportunity in response.opportunities
            if opportunity.list_id == list_id
        ]

        if len(valid_opportunities) == 1:
            return valid_opportunities[0]

        if len(valid_opportunities) > 1:
            self.__logger.error(f'Multiple results found for {name}')
            self.__logger.error(valid_opportunities)

            raise affinity_types.MultipleResults(f'Multiple results found for {name}')

        return None

    def create_opportunity(self, new_opportunity: affinity_types.NewOpportunity) -> affinity_types.Opportunity:
        self.__logger.info(f'Creating opportunity - {new_opportunity.name}')
        return self._send_request(
            method='post',
            url=self.__url('opportunities'),
            result_type=affinity_types.Opportunity,
            json=new_opportunity.model_dump()
        )

    def update_person(self, person_id: int, new_person: affinity_types.NewPerson) -> affinity_types.Person:
        self.__logger.info(f'Updating person - {person_id}')
        return self._send_request(
            method='put',
            url=self.__url(f'persons/{person_id}'),
            json=new_person.model_dump(),
            result_type=affinity_types.Person
        )

    def update_company(self, company_id: int, new_company: affinity_types.NewCompany) -> affinity_types.Company:
        self.__logger.info(f'Updating company - {company_id}')
        return self._send_request(
            method='put',
            url=self.__url(f'organizations/{company_id}'),
            json=new_company.model_dump(),
            result_type=affinity_types.Company
        )

    def update_opportunity(
            self,
            opportunity_id: int,
            name: str | None = None,
            person_ids: list[int] | None = None,
            organization_ids: list[int] | None = None
    ) -> affinity_types.Opportunity:
        self.__logger.info(f'Updating opportunity - {opportunity_id}')
        name_field = {'name': name} if name else {}
        person_ids_field = {'person_ids': person_ids} if person_ids else {}
        organization_ids_field = {'organization_ids': organization_ids} if organization_ids else {}
        return self._send_request(
            method='put',
            url=self.__url(f'opportunities/{opportunity_id}'),
            json=name_field | person_ids_field | organization_ids_field,
            result_type=affinity_types.Opportunity
        )

    def fetch_all_list_entries(self, list_id: int) -> list[affinity_types.ListEntry]:
        self.__logger.debug(f'Fetching list entries - {list_id}')
        return self._send_request(
            method='get',
            url=self.__url(f'lists/{list_id}/list-entries'),
            result_type=list[affinity_types.ListEntry]
        )

    def create_list_entry(
            self,
            list_id: int,
            entity_id: int,
    ) -> affinity_types.ListEntry:
        self.__logger.info(f'Creating list entry - {list_id} - {entity_id}')
        return self._send_request(
            method='post',
            url=self.__url(f'lists/{list_id}/list-entries'),
            result_type=affinity_types.ListEntry,
            json={'entity_id': entity_id}
        )

    def fetch_all_entity_files(
            self,
            entity_id: int,
            entity_type: Literal['person', 'company', 'opportunity']
    ) -> list[affinity_types.EntityFile]:
        self.__logger.debug(f'Fetching entity files - {entity_id} - {entity_type}')
        return self._send_request(
            method='get',
            url=self.__url('entity-files'),
            params={
                'person_id': entity_id if entity_type == 'person' else None,
                'organization_id': entity_id if entity_type == 'company' else None,
                'opportunity_id': entity_id if entity_type == 'opportunity' else None
            },
            result_type=affinity_types.EntityFilesResponse
        ).entity_files

    def add_file_to_entity(
            self,
            entity_id: int,
            entity_type: Literal['person', 'company', 'opportunity'],
            file_name: str,
            file: bytes,
            file_type: str
    ) -> affinity_types.SuccessResponse:
        self.__logger.info(f'Adding file to {entity_type} - {entity_id} - {file_name}')
        return self._send_request(
            method='post',
            url=self.__url('entity-files'),
            params={
                'person_id': entity_id if entity_type == 'person' else None,
                'organization_id': entity_id if entity_type == 'company' else None,
                'opportunity_id': entity_id if entity_type == 'opportunity' else None
            },
            files=[
                ('file', (file_name, file, file_type))
            ],
            result_type=affinity_types.SuccessResponse
        )

    def add_note_to_entity(
            self,
            entity_id: int,
            entity_type: Literal['person', 'company', 'opportunity'],
            creator_id: int,
            note: str
    ) -> affinity_types.Note:
        self.__logger.info(f'Adding note to {entity_type} - {entity_id}')
        return self._send_request(
            method='post',
            url=self.__url('notes'),
            json={
                'content': note,
                'person_ids': [entity_id] if entity_type == 'person' else None,
                'organization_ids': [entity_id] if entity_type == 'company' else None,
                'opportunity_ids': [entity_id] if entity_type == 'opportunity' else None,
                'creator_id': creator_id,
                'type': 0
            },
            result_type=affinity_types.Note
        )

    def __fetch_interactions_page(
            self,
            interaction_type: Literal['meeting', 'call', 'chat message', 'email'],
            entity_type: Literal['person', 'company', 'opportunity'],
            entity_id: int,
            start_date: datetime.date,
            end_date: datetime.date,
            next_page_token: str | None
    ) -> affinity_types.EmailInteractionQueryResponse | affinity_types.CallOrMeetingInteractionQueryResponse:
        self.__logger.debug('Doing fetch interactions pagination call')
        print('Doing fetch interactions pagination call')

        interaction_number = {
            'meeting': 0,
            'call': 1,
            'chat message': 2,
            'email': 3
        }[interaction_type]

        return self._send_request(
            method='get',
            url=self.__url('interactions'),
            params={
                'type': interaction_number,
                'person_id': entity_id if entity_type == 'person' else None,
                'organization_id': entity_id if entity_type == 'company' else None,
                'opportunity_id': entity_id if entity_type == 'opportunity' else None,
                'start_time': datetime.datetime.combine(start_date, datetime.datetime.min.time()).isoformat(),
                'end_time': datetime.datetime.combine(end_date, datetime.datetime.min.time()).isoformat(),
                'page_token': next_page_token
            },
            result_type=Union[
                affinity_types.EmailInteractionQueryResponse,
                affinity_types.CallOrMeetingInteractionQueryResponse,

            ]
        )

    def fetch_all_interactions_in_period(
            self,
            interaction_type: Literal['meeting', 'call', 'chat message', 'email'],
            entity_type: Literal['person', 'company', 'opportunity'],
            entity_id: int,
            start_date: datetime.date,
            end_date: datetime.date
    ) -> list[affinity_types.EmailInteraction] | list[affinity_types.CallOrMeetingInteraction]:
        self.__logger.debug('Fetching interactions')
        response = self.__fetch_interactions_page(
            interaction_type=interaction_type,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            next_page_token=None
        )

        interactions = response.get_results()

        while response.next_page_token:
            response = self.__fetch_interactions_page(
                interaction_type=interaction_type,
                entity_type=entity_type,
                entity_id=entity_id,
                start_date=start_date,
                end_date=end_date,
                next_page_token=response.next_page_token
            )

            interactions.extend(response.get_results())

        return interactions

    def fetch_all_interactions(
            self,
            interaction_type: Literal['meeting', 'call', 'chat message', 'email'],
            entity_type: Literal['person', 'company', 'opportunity'],
            entity_id: int,
            start_date: datetime.date = datetime.date(2021, 1, 1),
    ) -> list[affinity_types.EmailInteraction] | list[affinity_types.CallOrMeetingInteraction]:
        self.__logger.debug(f'Fetching interactions from {start_date}')
        start_date = start_date
        end_date = min(start_date + datetime.timedelta(days=364), datetime.date.today())
        interactions = []

        while start_date < datetime.date.today():
            interactions.extend(self.fetch_all_interactions_in_period(
                interaction_type=interaction_type,
                entity_type=entity_type,
                entity_id=entity_id,
                start_date=start_date,
                end_date=end_date
            ))

            start_date = end_date + datetime.timedelta(days=1)
            end_date = min(start_date + datetime.timedelta(days=364), datetime.date.today())

        return interactions

    def get_all_webhooks(self) -> list[affinity_types.Webhook]:
        self.__logger.debug('Fetching all webhooks')
        return self._send_request(
            method='get',
            url=self.__url('webhook'),
            result_type=list[affinity_types.Webhook]
        )

    def delete_webhook(self, webhook_id: int) -> None:
        self.__logger.info(f'Deleting webhook - {webhook_id}')
        self._send_request(
            method='delete',
            url=self.__url(f'webhook/{webhook_id}'),
            result_type=affinity_types.SuccessResponse
        )

    def create_webhook(self, url: str, events: list[affinity_types.WebhookEventType]):
        self.__logger.info(f'Creating webhook - {url}, {events}')
        return self._send_request(
            method='post',
            url=self.__url('webhook/subscribe'),
            result_type=affinity_types.Webhook,
            json={
                'webhook_url': url,
                'subscriptions': events
            }
        )
