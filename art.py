import click
import hashlib
import requests
from tabulate import tabulate


URL = "http://10.0.0.100:8000/api"


@click.group()
@click.option('--url', default=URL, help="default connection url current: '%s'" % URL)
@click.pass_context
def cli(ctx, url):
    ctx.obj = {'url': url}


@click.command()
@click.option('-bm', '--base-manifest', required=True, type=click.File('rb'))
@click.option('-tm', '--target-manifest', required=True, type=click.File('rb'))
@click.pass_context
def compare(ctx, base_manifest, target_manifest):

    api_url = ctx.obj['url']
    try:
        data = {
            "manifest_1": hashlib.sha1(base_manifest.read()).hexdigest(),
            "manifest_2": hashlib.sha1(base_manifest.read()).hexdigest()
        }

        response = requests.get("%s/compare/manifest/" % api_url, timeout=10, data=data)

        data = response.json()

        # XXX this is just to present table thing, change to "data" when tests data arrives
        table = [["Sun", 696000, 1989100000],
                 ["Earth", 6371, 5973.6],
                 ["Moon", 1737, 73.5],
                 ["Mars", 3390, 641.85]]

        click.echo(tabulate(table))

    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


cli.add_command(compare)


def main():
    cli()

if __name__ == '__main__':
    cli()
