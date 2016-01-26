#!/usr/bin/python
import os
import sys
import json
import httplib
import logging

from urlparse import urljoin, urlsplit


logging.basicConfig(format='%(levelname)s:  %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
httplib.HTTPConnection.debuglevel = 1


RESULT_ENDPOINT = "/api/result/"


def _push_object(auth_pw, backend_url, endpoint, params):
    usplit = urlsplit(backend_url)
    url = urljoin(backend_url, endpoint)

    logger.info("Submitting to URL: %s" % url)

    headers = {
        "Content-type": "application/json",
        "Accept": "application/json",
        "Authorization": "Token %s" % auth_pw
    }

    conn = None
    if usplit.scheme.lower() == "http":
        conn = httplib.HTTPConnection(usplit.netloc)
    if usplit.scheme.lower() == "https":
        conn = httplib.HTTPSConnection(usplit.netloc)

    if conn is None:
        print "Unknown scheme: %s" % usplit.scheme
        sys.exit(1)

    conn.request("POST", endpoint, json.dumps(params), headers)

    response = conn.getresponse()
    if response.status < 300:
        return response.read()
    else:
        logger.warn(response.status)
        logger.warn(response.reason)
        logger.warn(response.read())
    return []


def _get_manifest(workspace_path):
    manifest_path = workspace_path + "pinned-manifest.xml"
    print "Searching for: %" % manifest_path
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as manifest_file:
            return manifest_file.read()
    print "Manifest not found"
    return None


def _get_test_jobs(workspace_path):
    test_jobs = ""
    for root, dirs, files in os.walk(workspace_path):
        for f in files:
            if f.startswith("lava-job-info-"):
                print "Opening %s/%s" % (root, f)
                with open("%s/%s" % (root, f), 'r') as info_file:
                    lava_info = json.load(info_file)
                    test_job_ids = ",".join(lava_info['job_id'])
                    print "LAVA job IDs to add: %s" % test_job_ids
                    if len(test_jobs) == 0:
                        test_jobs = test_job_ids
                    else:
                        test_jobs = test_jobs + "," + test_job_ids

    return test_jobs


if __name__ == '__main__':
    jenkins_project_name = os.environ.get("JOB_NAME")

    jenkins_build_number = os.environ.get("BUILD_NUMBER")
    jenkins_build_id = os.environ.get("BUILD_ID")
    jenkins_build_url = os.environ.get("BUILD_URL")

    branch_name = os.environ.get("LOCAL_MANIFEST_BRANCH")

    art_url = os.environ.get("ART_URL", "http://localhost:8000/")
    art_token = os.environ.get("ART_TOKEN")

    manifest = _get_manifest(os.environ.get("WORKSPACE"))
    test_jobs = _get_test_jobs("/home/buildslave/srv/%s/android/out/" % jenkins_project_name)

    if jenkins_build_number is None:
        print "Build number not set. Exiting!"
        sys.exit(1)
    if jenkins_project_name is None:
        print "Project name not set. Exiting!"
        sys.exit(1)
    if jenkins_build_url is None:
        print "Build URL not set. Exiting!"
        sys.exit(1)
    if art_token is None:
        print "ART token not set. Exiting!"
        sys.exit(1)
    if not manifest:
        print "Manifest missing. Exiting!"
        sys.exit(1)

    print "Registered test jobs: %s" % test_jobs

    params = {
        'name': jenkins_project_name,

        'build_id': jenkins_build_id,
        'build_url': jenkins_build_url,
        'build_number': jenkins_build_number,

        'test_jobs': test_jobs,
        'manifest': manifest,
        'branch_name': branch_name,

        "gerrit_change_number": os.environ.get("GERRIT_CHANGE_NUMBER"),
        "gerrit_patchset_number":os.environ.get("GERRIT_PATCHSET_NUMBER"),
        "gerrit_change_url": os.environ.get("GERRIT_CHANGE_URL"),
        "gerrit_change_id": os.environ.get("GERRIT_CHANGE_ID", "")
    }

    print params

    _push_object(art_token, art_url, RESULT_ENDPOINT, params)
