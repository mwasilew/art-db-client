import click
import hashlib
import requests
import sys
from math import pow, sqrt
from netrc import netrc
from urlparse import urlparse, urljoin
from tabulate import tabulate

import logging
#logger = logging.getlogger(__name__)
logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.WARNING)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.ERROR)
requests_log.propagate = True

URL = "https://art-reports.linaro.org/api/"

def get_rest_objects(url, params, headers):
    s = requests.Session()
    r = requests.Request('GET',
            url,
            params=params,
            headers=headers)
    prep = r.prepare()
    response = s.send(prep)
    if response.status_code == 401:
        click.echo(click.style("Unauthorized", fg='red'))
        sys.exit(1)
    if response.status_code == 500:
        click.echo(click.style("Internal server error", fg='red'))
        sys.exit(1)

    res = response.json()
    if isinstance(res, dict) and 'results' in res.keys():
        # this happens when there is 'limit' applied in params
        return res['results']
    return res

@click.group()
@click.option('--url', default=URL, help="default connection url current: '%s'" % URL)
@click.option('--auth', default="", required=False, help="authentication token")
@click.pass_context
def cli(ctx, url, auth):
    password = None
    if auth == "":
        # try obtaining token from .netrc
        urlparser = urlparse(url)
        netrcauth = netrc()
        try:
            login, account, password = netrcauth.authenticators(urlparser[1]) # netloc
        except:
            sys.exit(1)
    else:
        password = auth
    if not password:
        click.echo(click.style("No token found in .netrc", fg='red'))
        sys.exit(1)
    ctx.obj = {'url': url, 'auth': password}


@click.command()
@click.argument('num_manifests', required=True, nargs=1)
@click.pass_context
def list(ctx, num_manifests):
    api_url = ctx.obj['url']
    auth = ctx.obj['auth']
    try:
        data = {
            "fields": "id",
            "limit": num_manifests
        }

        headers = {"Authorization": "Token %s" % auth}

        url = urljoin(api_url, "manifest/")
        manifests = get_rest_objects(url, data, headers)

        table = [['Manifest ID', 'Results']]
        for manifest in manifests:
            table.append([manifest['id'], ''])
            data = {
                "manifest": manifest,
                "fields": "branch,gerrit_change_id,gerrit_change_number,gerrit_patchset_number"
            }
            url = urljoin(api_url, "result/")
            results = get_rest_objects(url, data, headers)
            resultset = set()
            for result in results:
                change_number = result.get('gerrit_change_number', 'base')
                if change_number == 'base' or change_number is None:
                    resultset.add('base')
                else:
                    resultset.add("%s/%s" % (change_number, result.get('gerrit_patchset_number', 1)))
            for result in resultset:
                table.append(['', result])

        click.echo(tabulate(table, headers="firstrow"))

    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


@click.command()
@click.argument('manifest_id', required=True, nargs=1)
@click.argument('manifest_file_name', required=True, nargs=1, type=click.File('wb'))
@click.pass_context
def manifest(ctx, manifest_id, manifest_file_name):
    api_url = ctx.obj['url']
    auth = ctx.obj['auth']
    try:
        data = {
            "id": manifest_id
        }

        headers = {"Authorization": "Token %s" % auth}

        url = urljoin(api_url, "manifest/")
        manifest = get_rest_objects(url, data, headers)
        if len(manifest) == 1:
            manifest_file_name.write(manifest[0]['manifest'])
        else:
            click.echo(click.style("No manifest with ID %s found" % manifest_id, fg='red'))

    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


@click.command()
@click.argument('patchset', required=False, nargs=1)
@click.pass_context
def details(ctx, patchset):
    api_url = ctx.obj['url']
    auth = ctx.obj['auth']
    try:
        data = {}
        if patchset:
            gerrit_change_number, gerrit_patchset_number = patchset.split("/", 1)
            data = {
                "gerrit_change_number": gerrit_change_number,
                "gerrit_patchset_number": gerrit_patchset_number
            }

        headers = {"Authorization": "Token %s" % auth}

        url = urljoin(api_url, "details/")
        response = get_rest_objects(url, data, headers)
        results = response['data']
        metadata = response['metadata']
        click.echo(tabulate(metadata.items()))

        table = [['Name', 'Average', 'Std dev', 'Iterations']]
        for score in results:
            table.append(["%s_%s" % (score['benchmark'], score['subscore']),
                score['measurement__avg'],
                score['measurement__stddev'],
                score['measurement__count']])

        click.echo(tabulate(table, headers="firstrow"))
    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


def find_matching_dict(base_dict, list_of_dicts):
    for d in list_of_dicts:
        if d['benchmark'] == base_dict['benchmark'] and \
                d['subscore'] == base_dict['subscore']:
            return d

@click.command()
@click.option('--patchset', required=True, nargs=1)
@click.option('--base', required=False, nargs=1)
@click.pass_context
def compare(ctx, patchset, base):
    api_url = ctx.obj['url']
    auth = ctx.obj['auth']
    try:
        data = {}
        gerrit_change_number, gerrit_patchset_number = patchset.split("/", 1)
        data = {
            "gerrit_change_number": gerrit_change_number,
            "gerrit_patchset_number": gerrit_patchset_number
        }

        headers = {"Authorization": "Token %s" % auth}

        url = urljoin(api_url, "details/")
        patchset_data = get_rest_objects(url, data, headers)
        patchset_results = patchset_data['data']
        patchset_metadata = patchset_data['metadata']

        url = urljoin(api_url, "result/")
        data.update({"fields": "manifest"})
        manifest_results = get_rest_objects(url, data, headers)
        base_manifest_id = None
        if base:
            base_manifest_id = base
        elif len(manifest_results) == 1:
            base_manifest_id = manifest_results[0]['manifest']
        else:
            # base should be the latest manifest?
            pass

        data = {
            "manifest": base_manifest_id
        }
        url = urljoin(api_url, "details/")
        base_data = get_rest_objects(url, data, headers)
        base_results = base_data['data']
        base_metadata = base_data['metadata']

        meta_table = [["", "patch", "base"]]
        for key in patchset_metadata.keys():
            meta_table.append([
                key,
                patchset_metadata.get(key, "--"),
                base_metadata.get(key, "--")
            ])

        click.echo(tabulate(meta_table, headers="firstrow"))

        table = [['Name', '% diff', 'Base value', '#base', '#patched']]
        for result in base_results:
            patchset = find_matching_dict(result, patchset_results)
            diff = (result['measurement__avg'] - patchset['measurement__avg'])/result['measurement__avg']
            diff_error = sqrt(pow(result['measurement__stddev'],2) + pow(patchset['measurement__stddev'],2))
            base = result['measurement__avg']
            base_count = result['measurement__count']
            patchset_count = patchset['measurement__count']
            table.append(["%s_%s" % (result['benchmark'], result['subscore']),
                "%s +- %s" % (100*diff, diff_error),
                base,
                base_count,
                patchset_count])
        click.echo(tabulate(table, headers="firstrow"))

    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


cli.add_command(list)
cli.add_command(manifest)
cli.add_command(details)
cli.add_command(compare)


def main():
    cli()

if __name__ == '__main__':
    cli()
