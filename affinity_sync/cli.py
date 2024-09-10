import datetime
import io
import json
import logging
import logging.config
import os

import click
import plotille
import tabulate
from rich import console as rich_console

from . import clients
from . import sync as sync_import
from .module_types import db_types


class RichGroup(click.Group):

    def format_help(self, ctx, formatter):
        commands = []

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)

            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        sio = io.StringIO()
        console = rich_console.Console(file=sio, force_terminal=True)

        console.print(f"""
         █████╗ ███████╗███████╗██╗███╗   ██╗██╗████████╗██╗   ██╗     ███████╗██╗   ██╗███╗   ██╗ ██████╗
        ██╔══██╗██╔════╝██╔════╝██║████╗  ██║██║╚══██╔══╝╚██╗ ██╔╝     ██╔════╝╚██╗ ██╔╝████╗  ██║██╔════╝
        ███████║█████╗  █████╗  ██║██╔██╗ ██║██║   ██║    ╚████╔╝█████╗███████╗ ╚████╔╝ ██╔██╗ ██║██║     
        ██╔══██║██╔══╝  ██╔══╝  ██║██║╚██╗██║██║   ██║     ╚██╔╝ ╚════╝╚════██║  ╚██╔╝  ██║╚██╗██║██║     
        ██║  ██║██║     ██║     ██║██║ ╚████║██║   ██║      ██║        ███████║   ██║   ██║ ╚████║╚██████╗
        ╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝        ╚══════╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝
        """)
        console.print("[bold]Commands:")

        for subcommand, cmd in commands:
            console.print(" ",
                          f'[bold underline]{subcommand}',
                          f'    [italic][{", ".join(str(x.opts[0]) for x in cmd.params)}]',
                          f'\n  {cmd.__doc__.strip()} \n' if cmd.__doc__ else "\n"
                          )
        formatter.write(sio.getvalue())


def current_time() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.info(f'Logger created')


CONFIG_FIELDS = [
    'affinity-api-key',
    'postgres-host',
    'postgres-port',
    'postgres-user',
    'postgres-password',
    'postgres-database',
]


def fetch_config() -> dict | None:
    if os.path.exists('.affinity-sync-config'):
        with open('.affinity-sync-config', 'r') as f:
            return json.load(f)

    return None


def save_config(config: dict):
    with open('.affinity-sync-config', 'w') as f:
        json.dump(config, f)


def get_config() -> dict | None:
    config = fetch_config()

    if not config:
        click.echo('No config found. Run `affinity-sync config` to set up')
        return None

    return config


def config():
    """
    Set up config
    """
    existing_config = fetch_config() or {}
    new_config = {}

    for field in CONFIG_FIELDS:
        new_config[field] = click.prompt(
            text=f'{field}',
            default=existing_config.get(field),
            value_proc=lambda x: x.strip() if x else None
        )

    save_config(new_config)


def display_table(rows: list[dict]):
    if not rows:
        return

    headers = list(rows[0].keys())
    rows = [[row[header] for header in headers] for row in rows]

    click.echo(
        click.style(
            tabulate.tabulate(rows, headers=headers, tablefmt='grid'),
            fg='green'
        )
    )


@click.option('-live', is_flag=True, help='Only show live syncs')
@click.option('-list', is_flag=True, help='Only show list syncs')
@click.option('-view', is_flag=True, help='Only show view syncs')
@click.option('-people', is_flag=True, help='Only show people syncs')
@click.option('-companies', is_flag=True, help='Only show company syncs')
@click.option('-due', is_flag=True, help='Only show syncs that are due')
def ls(live: bool, list: bool, view: bool, people: bool, companies: bool, due: bool) -> int:
    """
    Show list of syncs
    """

    config = get_config()

    if not config:
        return -1

    client = clients.PostgresClient(
        host=config['postgres-host'],
        port=config['postgres-port'],
        user=config['postgres-user'],
        password=config['postgres-password'],
        dbname=config['postgres-database']
    )
    # Fetch all valid syncs
    syncs = client.fetch_syncs() if not due else client.fetch_due_syncs()

    if not syncs:
        sync_import.Sync(
            affinity_api_key=config['affinity-api-key'],
            db_host=config['postgres-host'],
            db_port=config['postgres-port'],
            db_user=config['postgres-user'],
            db_password=config['postgres-password'],
            db_name=config['postgres-database']
        ).set_up_syncs()
        syncs = client.fetch_syncs() if not due else client.fetch_due_syncs()

    # Filter to requested types
    filtered_syncs = [
        sync for sync in syncs
        if
        (not live or sync.live) and
        (not list or isinstance(sync, db_types.ListSync)) and
        (not view or isinstance(sync, db_types.ViewSync)) and
        (not people or isinstance(sync, db_types.PersonSync)) and
        (not companies or isinstance(sync, db_types.CompanySync))
    ]

    # Format the rows
    to_display = []

    views = client.fetch_rows(table='view_metadata')
    lists = client.fetch_rows(table='list_metadata')
    latest_logs = client.fetch_latest_log_per_sync()

    for sync in filtered_syncs:
        target = None

        if isinstance(sync, db_types.PersonSync):
            target = 'All People'

        if isinstance(sync, db_types.CompanySync):
            target = 'All Companies'

        if isinstance(sync, db_types.ListSync):
            target = next((list for list in lists if list.affinity_id == sync.data.affinity_list_id), None).name

        if isinstance(sync, db_types.ViewSync):
            target_view = next((view for view in views if view.affinity_id == sync.data.affinity_view_id), None).name
            target_list = next((list for list in lists if list.affinity_id == sync.data.affinity_list_id), None).name
            target = f'{target_view} ({target_list})'

        latest_log = next((log for log in latest_logs if log.sync_id == sync.id), None)

        if not latest_log:
            last_run_text = 'Never Run'

        else:
            logged_at = latest_log.created_at.replace(tzinfo=datetime.timezone.utc)
            minutes_ago = int((current_time() - logged_at).total_seconds() / 60)
            last_run_text = f'{latest_log.created_at.strftime("%Y-%m-%d %H:%M:%S")} ({minutes_ago} minutes ago)'

        to_display.append({
            'ID': sync.id,
            'Target': target,
            'Type': sync.type,
            'Ignore Views': 'N/A' if not isinstance(sync, db_types.ListSync) else sync.data.ignore_views,
            'Live': 'Yes' if sync.live else 'No',
            'Frequency': f'{sync.frequency_minutes} minutes',
            'Last Run': last_run_text
        })

    # Display the table
    display_table(to_display)

    return len(to_display)


@click.option('--n', default=10, help='Show the n latest logs')
def show_logs(n: int):
    """
    Show the sync logs
    """
    config = get_config()

    if not config:
        return

    client = clients.PostgresClient(
        host=config['postgres-host'],
        port=config['postgres-port'],
        user=config['postgres-user'],
        password=config['postgres-password'],
        dbname=config['postgres-database']
    )

    logs = client.fetch_latest_logs(n)
    syncs = client.fetch_syncs()
    views = client.fetch_rows(table='view_metadata')
    lists = client.fetch_rows(table='list_metadata')

    to_display = []

    for log in logs:
        sync = next((sync for sync in syncs if sync.id == log.sync_id), None)
        target = None

        if isinstance(sync, db_types.PersonSync):
            target = 'All People'

        if isinstance(sync, db_types.CompanySync):
            target = 'All Companies'

        if isinstance(sync, db_types.ListSync):
            target = next((list for list in lists if list.affinity_id == sync.data.affinity_list_id), None).name

        if isinstance(sync, db_types.ViewSync):
            target_view = next((view for view in views if view.affinity_id == sync.data.affinity_view_id), None).name
            target_list = next((list for list in lists if list.affinity_id == sync.data.affinity_list_id), None).name
            target = f'{target_view} ({target_list})'

        logged_at = log.created_at.replace(tzinfo=datetime.timezone.utc)
        minutes_ago = int((current_time() - logged_at).total_seconds() / 60)
        to_display.append({
            'Sync ID': log.sync_id,
            'Target': target,
            'Type': sync.type,
            'Ran At': f'{log.created_at.strftime("%Y-%m-%d %H:%M:%S")} ({minutes_ago} minutes ago)'
        })

    display_table(to_display)


def sync():
    """
    Run any due syncs
    """

    config = get_config()

    if not config:
        return

    runner = sync_import.Sync(
        affinity_api_key=config['affinity-api-key'],
        db_host=config['postgres-host'],
        db_port=config['postgres-port'],
        db_user=config['postgres-user'],
        db_password=config['postgres-password'],
        db_name=config['postgres-database']
    )

    number_to_run = ls(live=False, list=False, view=False, people=False, companies=False, due=True)

    if number_to_run == -1:
        return

    if number_to_run == 0:
        click.echo('No syncs to run')
        return

    click.confirm(f'Are you sure you want to run the above {number_to_run} syncs?', abort=True)

    setup_logging()
    runner.run()


@click.option('-plot', is_flag=True, help='Plot the credits')
def api_credits(plot: bool):
    """
    Show the remaining API credits
    """
    config = get_config()

    if not config:
        return

    client = clients.PostgresClient(
        host=config['postgres-host'],
        port=config['postgres-port'],
        user=config['postgres-user'],
        password=config['postgres-password'],
        dbname=config['postgres-database']
    )
    credits = client.fetch_call_entitlements()

    if not plot:

        if not credits:
            click.echo('No credit logs - perform a sync first')

        click.echo(
            f'As of the last sync, you have {credits[0].org_remaining}/{credits[0].org_limit} credits remaining for'
            f' the month ({credits[0].user_remaining}/{credits[0].user_limit} remaining this minute).'
        )

    else:
        counts = [credit.org_remaining for credit in credits]
        days_ago = [
            (credit.inserted_at.replace(tzinfo=datetime.timezone.utc)
             - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds() / (60 * 60 * 24)
            for credit in credits
        ]

        plot = plotille.plot(
            X=days_ago,
            X_label="Days Ago",
            Y=counts,
            Y_label="Credits Remaining",
            height=10,
            width=100,
            interp="linear",
            lc="green",
            origin=False
        )

        click.echo(plot)


def update_sync():
    """
    Perform updates on the sync schedules
    """
    config = get_config()

    if not config:
        return

    client = clients.PostgresClient(
        host=config['postgres-host'],
        port=config['postgres-port'],
        user=config['postgres-user'],
        password=config['postgres-password'],
        dbname=config['postgres-database']
    )
    current_syncs = client.fetch_syncs()

    sync_type = click.prompt(
        text='Which type of sync would you like to update?',
        type=click.Choice(['list', 'view', 'person', 'company'])
    )
    apply_to_all = click.confirm(text='Apply to all syncs of this type?')

    if apply_to_all:
        syncs_to_update = [sync for sync in current_syncs if sync.type == sync_type]

    else:
        sync_id = click.prompt(
            text='Which sync would you like to update? (ID)',
            type=int
        )
        syncs_to_update = [sync for sync in current_syncs if sync.id == sync_id]

    update_type = click.prompt(
        text='What would you like to update?',
        type=click.Choice(['frequency', 'live'] + (['ignore_views'] if sync_type == 'list' else []))
    )
    new_value = None

    if update_type == 'frequency':
        new_value = click.prompt(
            text='What would you like the new frequency to be? (in minutes)',
            type=int
        )

    elif update_type == 'live':
        new_value = click.confirm(text='Should the sync be live?')

    elif update_type == 'ignore_views':
        new_value = click.confirm(text='Should the sync ignore views?')

    else:
        raise ValueError('Invalid update type')

    for sync in syncs_to_update:
        if update_type == 'frequency':
            sync.frequency_minutes = new_value
        elif update_type == 'live':
            sync.live = new_value
        elif update_type == 'ignore_views':
            sync.data.ignore_views = new_value

        client.update_sync(sync)

    click.echo(f'Updated {len(syncs_to_update)} syncs')


@click.group(cls=RichGroup)
def cli():
    pass


cli.add_command(click.command()(config))
cli.add_command(click.command()(ls))
cli.add_command(click.command()(show_logs))
cli.add_command(click.command()(sync))
cli.add_command(click.command()(api_credits))
cli.add_command(click.command()(update_sync))

if __name__ == '__main__':
    cli()
