import logging
from typing import Literal

import requests

from . import affinity_base
from ..module_types import affinity_v1_api as affinity_types


class AffinityClientV1(affinity_base.AffinityBase):
    __URL = 'https://api.affinity.co/'

    def __init__(self, api_key: str):
        self.__logger = logging.getLogger('AffinityClientV1')
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

    def find_person_by_name(self, first_name: str, last_name: str) -> affinity_types.Person | None:
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
            result_type=affinity_types.DeleteResponse
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
            new_opportunity: affinity_types.NewOpportunity
    ) -> affinity_types.Opportunity:
        self.__logger.info(f'Updating opportunity - {opportunity_id}')
        return self._send_request(
            method='put',
            url=self.__url(f'opportunities/{opportunity_id}'),
            json=new_opportunity.model_dump(),
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
