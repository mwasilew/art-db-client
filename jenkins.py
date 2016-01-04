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
    parser = argparse.ArgumentParser(
        description='Upload data to ART instance')

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
