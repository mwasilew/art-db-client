import sys
import requests
import argparse


def colon_separted_type(item):
    value = item.split(":")
    if len(value) != 2 or not value[0] or not value[1]:
        raise argparse.ArgumentTypeError(
            "should be in form ITEM_NAME:ITEM_VALUE")
    return value

def pretty_errors(errors):
    return ", ".join(
        ['"%s" - %s' % (error, ", ".join(messages).lower())
         for error, messages in errors.items()])


def main():
    description = """
    the script is responsible for pushing the data from jenkins instance to ART server.
    It should be called with instance URL and TOKEN along with and VALUES list.

    The VALUES is a list passed in space separated pair NAME:VALUE [NAME:VALUE].
    The minimum required list is one with the id.

    Examples:\n

    - jenkins.py http://art-instance.org a05d8394aa22806 id:12341234
    - jenkins.py http://art-instance.org a05d8394aa22806 id:12341234 url:http://jenkins-server/job/1234
    """

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('url', help='Instance url')
    parser.add_argument('token', help='Authentication token')
    parser.add_argument('values', nargs='+',
                        metavar='item_name:item_value',
                        type=colon_separted_type,
                        help='List of values to send to ART instance')

    args = parser.parse_args()
    try:
        headers = {"Authorization": "Token %s" % args.token}
        data = dict(args.values)

        response = requests.post(args.url, headers=headers, data=data)

        if response.status_code == requests.codes.ok:
            sys.stdout.write("OK\n")
            sys.exit()

        if response.status_code == requests.codes.bad:
            errors = pretty_errors(response.json())
            sys.stderr.write("Validation Errors: %s\n" % errors)
            sys.exit(1)

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        sys.stderr.write("Error: %s\n" % str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
