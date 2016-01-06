import csv
import datetime
import json
import requests
import sys

from netrc import netrc
from optparse import OptionParser
from urlparse import urljoin, urlsplit, urlparse

import logging
logging.basicConfig(level=logging.DEBUG)

MANIFEST_ENDPOINT = "manifest/"
RESULT_ENDPOINT = "result/"
RESULTDATA_ENDPOINT = "resultdata/"
BRANCH_ENDPOINT = "branch/"
BOARD_ENDPOINT = "board/"
BOARDCONFIGURATION_ENDPOINT = "boardconfiguration/"
BENCHMARK_ENDPOINT = "benchmark/"

def retrieve_object_list(backend, endpoint, params, headers):
    url = urljoin(backend, endpoint)
    response = requests.get(url, params=params, headers=headers)
    print response.request.headers
    #response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print response.status_code
        print response.reason
        print response.text
    return []

def push_object(backend, endpoint, params, headers):
    url = urljoin(backend, endpoint)
    s = requests.Session()
    r = requests.Request('POST',
            url,
            data=params,
            headers=headers)
    prep = r.prepare()
    print r.headers
    #headers.update({'Content-Type':'application/json'})
    #response = requests.post(url, data=params, headers=headers)
    response = s.send(prep)
    print response.request.headers
    #response = requests.post(url, data=params)
    #pprint.pprint(params)
    if response.status_code < 300:
        return response.json()
    else:
        print response.status_code
        print response.text
    return []

def main():
    parser = OptionParser()
    parser.add_option("--url", dest="backend_url",
                  help="Backend URL")
    parser.add_option("--manifest", dest="manifest",
                  help="manifest filename and path", metavar="FILE")
    parser.add_option("--result-file", dest="resultfile",
                  help="CSV formatted file with benchmark results", metavar="FILE")
    parser.add_option("--benchmark", dest="benchmark",
                  help="Benchmark name")
    parser.add_option("--board", dest="board",
                  help="Board name")
    parser.add_option("--boardconfig", dest="boardconfig",
                  help="Board Configuration name")
    parser.add_option("--branch", dest="branch",
                  help="Branch name")
    parser.add_option("--change-id", dest="change_id",
                  help="Gerrit change ID")
    parser.add_option("--patchset", dest="patchset",
                  help="Gerrit change number")
    parser.add_option("--change-number", dest="change_number",
                  help="Gerrit change number")
    parser.add_option("--change-url", dest="change_url",
                  help="Gerrit change URL")
    parser.add_option("--build-url", dest="build_url",
                  help="Jenkins build URL")
    parser.add_option("--token", dest="token",
                  help="API authorisation token")

    (options, args) = parser.parse_args()
    if not options.backend_url:
        parser.error("Backend URL is mandatory")
    if not options.manifest:
        parser.error("Manifest file name is mandatory")
    if not options.benchmark:
        parser.error("Benchmark name is mandatory")
    if not options.board:
        parser.error("Board name is mandatory")
    if not options.boardconfig:
        parser.error("Board Configurations name is mandatory")
    if not options.branch:
        parser.error("Branch name is mandatory")
    if not options.resultfile:
        parser.error("Result file name is mandatory")
    if not options.build_url:
        parser.error("Build URL is mandatory")

    token = None
    if options.token:
        print "Using token from command line"
        token = options.token
    else:
        print "Using token from .netrc"
        urlparser = urlparse(options.backend_url)
        netrcauth = netrc()
        try:
            login, account, token = netrcauth.authenticators(urlparser[1]) # netloc
        except:
            print "No account information found"
            sys.exit(1)
    headers = {"Authorization": "Token %s" % token}

    # check if manifest already existis
    manifest = None
    with open(options.manifest) as manifest_file:
        manifest_contents = manifest_file.read()
        params = {
            "manifest": manifest_contents
        }
        manifest = push_object(options.backend_url, MANIFEST_ENDPOINT, params, headers)

    if not manifest:
        # ToDo move to logging
        print "Something went wrong. Got no manifest in database!"
        sys.exit(1)

    params = {
        "name": options.benchmark
    }
    benchmark = push_object(options.backend_url, BENCHMARK_ENDPOINT, params, headers)
    if not benchmark:
        # ToDo move to logging
        print "Something went wrong. Got no benchmark in database!"
        sys.exit(1)

    params = {
        "name": options.boardconfig
    }
    boardconfig = push_object(options.backend_url, BOARDCONFIGURATION_ENDPOINT, params, headers)

    params = {
        "displayname": options.board,
        "display": options.board,
        "configuration": boardconfig['id']
    }
    board = push_object(options.backend_url, BOARD_ENDPOINT, params, headers)

    params = {
        "name": options.branch
    }
    branch = push_object(options.backend_url, BRANCH_ENDPOINT, params, headers)


    params = {
        "board":board['id'],
        "branch": branch['id'],
        "manifest": manifest['id'],
        "build_url": options.build_url
    }
    if options.change_id:
        params.update({"gerrit_change_id": options.change_id})
    if options.patchset:
        params.update({"gerrit_patchset_number": options.patchset})
    if options.change_number:
        params.update({"gerrit_change_number": options.change_number})
    if options.change_url:
        params.update({"gerrit_change_url": options.change_url})
    result = push_object(options.backend_url, RESULT_ENDPOINT, params, headers)

    params = {
        "benchmark": benchmark['id'],
        "result": result['id']
    }
    with open(options.resultfile) as resultfile:
        # result file should be CSV like object
        # with structure:
        # measurement_name, value
        csvreader = csv.reader(resultfile)
        for row in csvreader:
            params.update(
                {"name": row[0],
                "measurement": row[1]
                }
            )
            push_object(options.backend_url, RESULTDATA_ENDPOINT, params, headers)


if __name__ == "__main__":
    main()
