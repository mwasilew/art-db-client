import sys
import requests
import argparse


def colon_separted_type(item):
    value = item.split(":")
    if len(value) != 2 or not value[0] or not value[1]:
        raise argparse.ArgumentTypeError(
            "should be in form ITEM_NAME:ITEM_VALUE")
    return value


def main():
    parser = argparse.ArgumentParser(
        description='upload data to ART instance')

    parser.add_argument('url', help='ART instance url')

    parser.add_argument('values', metavar='item_name:item_value',
                        type=colon_separted_type, nargs='+',
                        help='a list of values to send to ART instance')

    args = parser.parse_args()
    try:
        response = requests.post(args.url, data=dict(args.values))
        response.raise_for_status()

        sys.stdout.write("OK\n")

    except requests.exceptions.RequestException as e:
        sys.stderr.write("Error: %s\n" % str(e))


if __name__ == '__main__':
    main()
