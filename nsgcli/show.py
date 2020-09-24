"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import datetime
import json
import click
import time
from typing import Dict, List, Any

from nsgcli.api import API
import nsgcli.system


@click.group()
@click.pass_context
def show(_: click.Context) -> None:
    pass

@show.command()
@click.pass_context
def status(ctx) -> None:
    """
    Print server status as JSON
    """
    api: API = ctx.obj['api']
    print(json.dumps(api.get_status(), indent=4))


@show.command()
@click.pass_context
def version(ctx: click.Context):
    """
    Print software version
    """
    api: API = ctx.obj['api']
    print(api.get_status()['version'])


@show.command()
@click.pass_context
def cache(ctx: click.Context) -> None:
    """
    List contents of the long- and short-term NsgQL cache
    """
    api: API = ctx.obj['api']
    print(json.dumps(api.get_cache_data(), indent=4))


show.add_command(nsgcli.system.system)


# TODO: check parameter, maybe do this differently
def transform_value(field_name: str, value: Any, outdated=False) -> Any:
    if field_name in ['updatedAt', 'localTimeMs']:
        updated_at_sec = float(value) / 1000
        value = datetime.datetime.fromtimestamp(updated_at_sec)
        suffix = ''
        if outdated and time.time() - updated_at_sec > 15:
            suffix = ' outdated'
        return value.strftime('%Y-%m-%d %H:%M:%S') + suffix
    return value


def list_views(api: API) -> None:
    """
    API call status returns a dictionary that has an item 'status' with value that is
    also a dictionary. This makes parsing response harder
    """
    status = api.get_status()
    format_nsg = '{0[id]:<4} {0[name]:<32} {0[type]:<12} {1:<20}'
    header = {'id': 'id', 'name': 'name', 'type': 'type'}
    print(format_nsg.format(header, 'updated_at'))
    print('-' * 60)
    for view in status['views']:
        updated_at = transform_value('updatedAt', view['updatedAt'])
        print(format_nsg.format(view, updated_at))


VIEW_DROP_KEYS = frozenset(['links', 'nodes', 'path', 'singleUser', 'defaultVar', 'rule', 'linkRule', 'generation'])


@show.command()
@click.pass_context
@click.argument('view_id', type=click.INT, required=False)
def views(ctx: click.Context, view_id):
    """
    Show map views defined in the system.
    Examples:
        show views          -- list all views defined in the system
        show views NNN      -- prints parameters that define the view with id=NNNN.
                               This data can not be used to export/import views at this time.
    """
    api: API = ctx.obj['api']
    if not view_id:
        list_views(api)
        return
    response = api.get_views(view_id)
    print(json.dumps({k: v for k, v in response.items() if k not in VIEW_DROP_KEYS}, indent=4))


@show.command()
@click.pass_context
@click.argument('device_id', type=click.INT, required=True)
@click.argument('field', nargs=-1)
def device(ctx: click.Context, device_id, field) -> None:
    """
    Inspect device identified by its device ID
    """
    api: API = ctx.obj['api']
    response = api.get_device_json(device_id)
    dev = json.loads(response.content)
    if field:
        print(json.dumps({x: dev.get(x, {}) for x in field}, indent=4))
    else:
        print(json.dumps(dev, indent=4))


def update_column_width(obj: Dict[str, str], column_name: str, col_wid_dict: Dict[str, int]) -> None:
    w = col_wid_dict.get(column_name, 0)
    txt = str(obj.get(column_name, ''))
    w = max(w, len(txt))
    col_wid_dict[column_name] = w


def convert_obj(obj: dict, columns: List[str]) -> dict:
    new_obj = obj.copy()
    # fill in required columns that may be missing in the object
    for col in columns:
        if col not in new_obj:
            new_obj[col] = ''
    updated_at = float(obj['updatedAt'])
    if updated_at == 0:
        new_obj['updatedAt'] = '--'
    else:
        new_obj['updatedAt'] = convert_updated_at(updated_at) + ' ago'
    return new_obj


def convert_updated_at(updated_at_ms: float) -> str:
    updated_at_sec = updated_at_ms / 1000.0
    value = datetime.datetime.fromtimestamp(updated_at_sec)
    delta = datetime.datetime.now() - value
    return str(delta - datetime.timedelta(microseconds=delta.microseconds))


@show.command()
@click.pass_context
def index(ctx: click.Context) -> None:
    """
    List NsgQL indexes and their cardinality
    """
    api: API = ctx.obj['api']
    response = api.get_index()

    ordered_columns = ['table', 'column', 'suffix', 'type', 'cardinality', 'redisKey', 'updatedAt']
    title: Dict[str, str] = {'table': 'table',
                             'column': 'column',
                             'suffix': 'ext',
                             'redisKey': 'redis',
                             'type': 'type',
                             'cardinality': 'cardinality',
                             'updatedAt': 'updatedAt'}
    resp = json.loads(response.content)
    column_width: Dict[str, int] = {}
    for column_name in title:
        update_column_width(title, column_name, column_width)
    for row in resp:
        converted = convert_obj(row, ordered_columns)
        for column_name in ordered_columns:
            update_column_width(converted, column_name, column_width)
    # assemble format string
    table_columns = []
    for column_name in ordered_columns:
        table_columns.append('{{0[{0}]:<{1}}}'.format(column_name, column_width.get(column_name)))
    format_str = u' | '.join(table_columns)
    title_line = format_str.format(title)
    print(title_line)
    print('-' * len(title_line))
    counter = 0
    for row in resp:
        converted = convert_obj(row, ordered_columns)
        print(format_str.format(converted))
        counter += 1
    print('-' * len(title_line))
    print('Total: {}'.format(counter))


@show.command()
@click.pass_context
def uuid(ctx: click.Context) -> None:
    """
    Print NSG cluster uuid
    """
    api: API = ctx.obj['api']
    print(api.get_status()['uuid'])


