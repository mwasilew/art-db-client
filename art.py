import click
import hashlib
import requests


URL = "http://10.0.0.100:8000/api"


@click.group()
def cli():
    pass


@click.command()
@click.argument('xml', type=click.File('rb'))
def manifest(xml):
    manifest_content = xml.read()
    hash = hashlib.sha1(manifest_content).hexdigest()

    response = requests.post("%s/manifest/" % URL,
                             data={"manifest": manifest_content})

    if response.status_code == 201:
        click.echo(click.style("Manifest: '%s' sent." % hash, fg='green'))

    elif response.status_code == 400:
        msg = "".join(["%s: %s" % (name, ", ".join(errors))
                       for name, errors in response.json().items()])

        click.echo(click.style('Upload Error: "%s"' % msg, fg='yellow'))
    else:
        click.echo(click.style("Upload Error", fg='red'))


# @click.argument('manifest', type=click.File('rb'))
@click.command()
def results():
    click.echo("Looking")


cli.add_command(manifest)
cli.add_command(results)

if __name__ == '__main__':
    cli()
