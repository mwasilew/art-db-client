import click
import hashlib
import requests


URL = "http://10.0.0.100:8000/api"


@click.group()
@click.option('--url', default=URL, help="default connection url current: '%s'" % URL)
@click.pass_context
def cli(ctx, url):
    ctx.obj = {'url': url}


@click.command(help="Uploads xml manifests")
@click.argument('manifest-file', type=click.File('rb'))
@click.pass_context
def manifest(ctx, manifest_file):
    api_url = ctx.obj['url']
    manifest_content = manifest_file.read()
    hash = hashlib.sha1(manifest_content).hexdigest()

    try:
        response = requests.post(
            "%s/manifest/" % api_url,
            timeout=10,
            data={"manifest": manifest_content})

        if response.status_code == 201:
            click.echo(click.style("Manifest: '%s' sent." % hash, fg='green'))

        elif response.status_code == 400:
            msg = "".join(["%s: %s" % (name, ", ".join(errors))
                           for name, errors in response.json().items()])
            click.echo(click.style("Upload Error: '%s'" % msg, fg='yellow'))
        else:
            click.echo(click.style("Upload Error", fg='red'))

    except requests.exceptions.ConnectionError:
        click.echo(click.style("Connection Error, server '%s' down?" % api_url, fg='red'))


@click.command()
def results():
    click.echo("Looking")


cli.add_command(manifest)
cli.add_command(results)


def main():
    cli()

if __name__ == '__main__':
    cli()
