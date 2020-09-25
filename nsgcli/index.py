"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
from nsgcli.api import API
import nsgcli.show


@click.group()
@click.pass_context
def index(_: click.Context) -> None:
    """
    Various operations on NsgQL indexes.
    """
    pass


@index.command()
@click.pass_context
def refresh(ctx: click.Context) -> None:
    """
    Refresh all NsgQL indexes
    """
    api: API = ctx.obj['api']
    api.print_response(api.index_command('refresh'))


@index.command()
@click.pass_context
def drop(ctx: click.Context) -> None:
    """
    Drop all NsgQL indexes
    """
    api: API = ctx.obj['api']
    api.print_response(api.index_command('drop'))


@index.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """
    List NsgQL indexes and their cardinality

    This is the same as `nsgcli show index`
    """
    nsgcli.show.index(ctx)


@index.command()
@click.pass_context
@click.argument('table', type=click.STRING)
@click.argument('column', type=click.STRING)
@click.argument('function', type=click.Choice(['tslast', 'tsmin', 'tsmax']), required=False)
def create(ctx: click.Context, table: str, column: str, function: str):
    """
    Create NsgQL index described by the table name and column name with optional function and boolean flag
    to make the index sort in descending order

    index create table_name column_name function_name

    The function is only applicable when column name is equal to 'metric'.

    Supported function names: tslast, tsmin, tsmax

    Examples:

         index create ifInRate ifDescription
         index create ifInRate metric tslast
         index create ifInRate metric tsmax

    """
    api: API = ctx.obj['api']
    api.print_response(api.index_create(table, column, function))
