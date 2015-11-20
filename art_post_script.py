#!/usr/bin/python

import ast
import base64
import json
import logging
import os
import pickle
import re
import requests
import shutil
import subprocess
import sys
import zipfile

try:
    import ConfigParser
except:
    # python3
    from configparser import ConfigParser

try:
    from xmlrpclib import ServerProxy
except:
    # python3
    from xmlrpc.client import ServerProxy
from optparse import OptionParser
try:
    from StringIO import StringIO
except:
    from io import StringIO

import xml.etree.ElementTree as ET
from jenkinsapi.jenkins import Jenkins
from urlparse import urljoin, urlsplit
from collections import OrderedDict

logging.basicConfig(format='%(levelname)s:  %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO)

MANIFEST_ENDPOINT           = "manifest/"
RESULT_ENDPOINT             = "result/"
RESULTDATA_ENDPOINT         = "resultdata/"
BRANCH_ENDPOINT             = "branch/"
BOARD_ENDPOINT              = "board/"
BOARDCONFIGURATION_ENDPOINT = "boardconfiguration/"
BENCHMARK_ENDPOINT          = "benchmark/"

class InfoRequestError(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return repr(self.reason)


class ArtDb(object):
    def __init__(self, backend_url, password):
        self.backend_url = backend_url
        self.auth_pw     = password

    def retrieve_object_list(backend_url, endpoint, params):
        url = urljoin(backend_url, endpoint)
        headers = {"Authorization": "Token %s" % self.auth_pw}
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(response.status_code)
            logger.warn(response.reason)
            logger.warn(response.text)
        return []

    def push_object(self, endpoint, params):
        url = urljoin(self.backend_url, endpoint)
        logger.info("Submitting to URL: %s" % url)
        headers = {"Authorization": "Token %s" % self.auth_pw}
        s = requests.Session()
        r = requests.Request('POST',
                url,
                data=params,
                headers=headers)
        prep = r.prepare()
        response = s.send(prep)

        if response.status_code < 300:
            return response.json()
        else:
            logger.warn(response.status_code)
            logger.warn(response.reason)
            logger.warn(response.text)
        return []

    def submit_result_to_db(self, data):
        params = {
            "manifest": data['manifest']
        }
        manifest = self.push_object(MANIFEST_ENDPOINT, params)

        params = {
            "name" : data['branch']
        }
        branch = self.push_object(BRANCH_ENDPOINT, params)
        for bench in data['test_result']:
            params = {
                "name" : bench['board_config']
            }
            boardconfig = self.push_object(BOARDCONFIGURATION_ENDPOINT, params)
            params = {
                "displayname"   : bench['board'],
                "display"       : bench['board'],
                "configuration" : boardconfig['id']
            }
            board = self.push_object(BOARD_ENDPOINT, params)
            params = {
                "board":                    board['id'],
                "branch":                   branch['id'],
                "manifest":                 manifest['id'],
                "build_url":                data['build_url'],
            }
            for key, value in data['gerrit_params'].items():
                if value:
                    params.update({key.lower: value})
                if key == "LOCAL_MANIFEST_BRANCH":
                    params.update({"branch": value})
            result = self.push_object(RESULT_ENDPOINT, params)
            params = {
                "name": bench['benchmark_name']
            }
            benchmark = self.push_object(BENCHMARK_ENDPOINT, params)
            params = {
                "benchmark": benchmark['id'],
                "result": result['id']
            }
            for t in bench['subscore']:
                params.update(t)
                logger.info("Submit: %s" % str(params))
                self.push_object(RESULTDATA_ENDPOINT, params)


class LinaroAndroidBuildSystem(object):
    def __init__(self, base_url, build_job,
                 username=None, password=None):
        logger.info("Jenkins build job: %s" %  build_job)
        self.base_url  = base_url
        self.build_job = build_job
        self.username  = username
        self.password  = password
        self.build_params = {}
        try:
            self.jenkins    = Jenkins(self.base_url, self.username, self.password)
            self.project    = self.jenkins[self.build_job]
        except:
            logger.error("Can not get Jenkins job: %s" % self.build_job)
            raise

    def get_build(self, build_no):
        try:
            build = self.project.get_build(build_no)
            return build
        except:
            logger.error("Can not get build: #%d" % build_no)
            raise

    def get_build_branch(self, build_no):
        if not self.build_params:
            self.get_build_parameters(build_no)
        build_params = {"BUILD_CONFIG_BRANCH": "",
                "BUILD_CONFIG_FILENAME": "",
                "BUILD_CONFIG_REPO": ""}
        for p in self.build_params:
            if p['name'] in build_params:
                build_params[p['name']] = p['value']
        # git clone build_config_repo -b build_branch repository
        command = ['git', 'clone', build_params["BUILD_CONFIG_REPO"], '-b', build_params["BUILD_CONFIG_BRANCH"], 'repository']
        subprocess.call(command)
        # workaround to ConfigParser limitation
        ini_str = '[root]\n' + open("repository/" + build_params["BUILD_CONFIG_FILENAME"], 'r').read()
        ini_fp = StringIO(ini_str)
        config = ConfigParser.RawConfigParser()
        config.readfp(ini_fp)
        branch = config.get("root", "LOCAL_MANIFEST_BRANCH")
        # check if not empty?
        command = ['rm', '-rf', 'repository']
        subprocess.call(command)
        return branch

    def get_build_test_job_ids(self, build_no):
        logger.info("Querying build #%d test job ids from Jenkins build job: %s" %
              (build_no, self.build_job))
        job_id_list = []
        build = self.get_build(build_no)
        job_id_list = re.findall("LAVA Job Id:\s\[?\'?(?P<master_job_id>[\d\.]+)", build.get_console())

        return job_id_list

    def get_build_manifest(self, build_no):
        manifest_file_name = "pinned-manifest.xml"
        rest_url = "%s/job/%s/%d/artifact/%s" % (self.base_url, self.build_job, build_no, manifest_file_name)
        manifest = requests.get(rest_url, auth=(self.username, self.password))
        if manifest.status_code != 200:
            raise InfoRequestError("[%s] %s" % (manifest.status_code, manifest.reason))
        else:
            return manifest.content

    def get_build_parameters(self, build_no):
        rest_url = "%s/job/%s/%d/api/json" % (self.base_url, self.build_job, build_no)
        req = requests.get(rest_url, auth=(self.username, self.password))
        if req.status_code != 200:
            raise InfoRequestError("[%s] %s" % (manifest.status_code, manifest.reason))
        else:
            build_info = req.json()
        try:
            self.build_params = (a['parameters'] for a in build_info['actions'] if 'parameters' in a).next()
        except:
            logger.error("Can not get build: #%d parameters." % build_no)
            raise

    def get_build_gerrit_parameters(self, build_no):
        if not self.build_params:
            self.get_build_parameters(build_no)
        gerrit_param = { "GERRIT_CHANGE_ID": "",
                         "GERRIT_PATCHSET_NUMBER": "",
                         "GERRIT_CHANGE_NUMBER": "",
                         "GERRIT_CHANGE_URL": ""}

        for p in self.build_params:
            if p['name'] in gerrit_param:
                gerrit_param[p['name']] = p['value']

        return gerrit_param


class LAVA(object):
    def __init__(self, username, token, lava_server="https://validation.linaro.org/"):
        try:
            self.lava_server = lava_server
            self.username    = username
            self.token       = token
            server_url       = "https://%s:%s@%sRPC2/" % (self.username, self.token, self.lava_server.split("//")[1])
            self.server      = ServerProxy(server_url)
            self.result_file_name = ""
        except:
            logger.warning("Can not connect to LAVA server: %s" % lava_server)
            raise

    def set_result_filename(self, result_file_name):
        self.result_file_name = result_file_name

    def get_test_results(self, job_no):
        test_result_list = []
        test_result = { "board": "",
                        "board_config": "",
                        "benchmark_name": "",
                        "subscore": [] }
        try:
            job_status = self.server.scheduler.job_status(job_no)
        except:
            logger.warning("Can not get any information for test job: %s" % job_no)
            raise

        if job_status['job_status'] != 'Complete':
            logger.warning("!!Job #%s is not completed.\n\tJob status: %s!! " % (job_no, job_status['job_status']))
        else:
            try:
                result_bundle = json.loads(self.server.dashboard.get(job_status['bundle_sha1'])['content'])
                target = (t for t in result_bundle['test_runs'] if t['test_id'] == 'multinode-target' or
                          t['test_id'] == 'lava-android-benchmark-target').next()
                host   = (t for t in result_bundle['test_runs'] if t['test_id'] == 'art-microbenchmarks' or
                          t['test_id'] == 'lava-android-benchmark-host').next()
                src = (s for s in host['software_context']['sources'] if 'test_params' in s).next()
            except:
                logger.warning("Job #%s seems not be a complete job, can not get test result" % job_no)
                raise
            # Get target device name
            test_result['board']        = target['attributes']['target']
            test_result['board_config'] = target['attributes']['target']
            # Get test name and test result
            if host['test_id'] == 'lava-android-benchmark-host':
                # This is a 3rd. party benchmark test
                test_result['benchmark_name'] = ast.literal_eval(src['test_params'])['TEST_NAME']
                # Get test results
                for t in host['test_results']:
                    if 'measurement' in t:
                        test_case = { "name": t['test_case_id'],
                                      "measurement" : t['measurement'] }
                        test_result['subscore'].append(test_case)
                test_result_list.append(test_result)
            else:
                # This is an art-microbenchmarks test
                # The test name and test results are in the attachmented pkl file
                # get test results for the attachment
                test_mode        = ast.literal_eval(src['test_params'])['MODE']
                json_content      = (a['content'] for a in host['attachments'] if a['pathname'].endswith('json')).next()
                json_text         = base64.b64decode(json_content)
                # save pickle file locally
                with open(self.result_file_name + "_" + str(test_mode) + ".json", "w") as json_file:
                    json_file.write(json_text)
                test_result_dict = json.loads(json_text)
                # Key Format: benchmarks/micro/<BENCHMARK_NAME>.<SUBSCORE>
                # Extract and unique them to form a benchmark name list
                test_result_keys = list(bn.split('/')[-1].split('.')[0] for bn in test_result_dict.keys())
                benchmark_list   = list(set(test_result_keys))
                for benchmark in benchmark_list:
                    test_result = {}
                    test_result['board']        = target['attributes']['target']
                    test_result['board_config'] = target['attributes']['target']
                    # benchmark iteration
                    test_result['benchmark_name'] = benchmark
                    test_result['subscore'] = []
                    key_word = "/%s." % benchmark
                    tests    = ((k, test_result_dict[k]) for k in test_result_dict.keys() if k.find(key_word) > 0)
                    for test in tests:
                        # subscore iteration
                        subscore = "%s_%s" % (test[0].split('.')[-1], test_mode)
                        for i in test[1]:
                            test_case = { "name": subscore,
                                          "measurement": i }
                            test_result['subscore'].append(test_case)

                    test_result_list.append(test_result)

        return test_result_list


if __name__ == '__main__':
    parser          = OptionParser()
    parser.add_option("--build-url", dest="build_url",
                        help="Specify the Jenkins build job url. This is MANDATORY.")
    parser.add_option("--backend-url", dest="backend_url",
                        help="Specify the backend database url. This is MANDATORY.")
    parser.add_option("--db-token", dest="backend_token",
                        help="Specify the backend db token. This is MANDATORY.")
    parser.add_option("--lava-url", dest="lava_url",
                        help="Specify the LAVA url. This is MANDATORY.")
    parser.add_option("--lava-user", dest="lava_user",
                        help="Specify the LAVA user. This is MANDATORY.")
    parser.add_option("--lava-token", dest="lava_token",
                        help="Specify the LAVA token. This is MANDATORY.")
    parser.add_option("--jenkins-user", dest="jenkins_user",
                        help="Specify the Jenkins user. This is MANDATORY.")
    parser.add_option("--jenkins-token", dest="jenkins_token",
                        help="Specify the Jenkins token. This is MANDATORY.")
    parser.add_option("--result-file-name", dest="result_file_name",
                        default="ubenchmarks",
                        help="Specify the Jenkins token. This is MANDATORY.")

    options, args = parser.parse_args()

    if not options.build_url:
        parser.error("Build URL is mandatory")
    if not options.backend_url:
        parser.error("Backend URL is mandatory")
    if not options.backend_token:
        parser.error("Backend Token is mandatory")
    if not options.lava_url:
        parser.error("LAVA url is mandatory")
    if not options.lava_user:
        parser.error("LAVA user is mandatory")
    if not options.lava_token:
        parser.error("LAVA token is mandatory")
    if not options.jenkins_user:
        parser.error("Jenkins user is mandatory")
    if not options.jenkins_token:
        parser.error("Jenkins token is mandatory")

    if options.build_url[len(options.build_url) - 1] != '/':
        url = options.build_url + '/'
    else:
        url = options.build_url
    ul = url.split('/')
    jenkins_build_number = ul[-2]
    jenkins_project      = ul[-3]
    jenkins_base_url     = '/'.join(ul[:-4])

    logger.info("build_no: %s\nproj: %s\nbase_url: %s" % (jenkins_build_number, jenkins_project, jenkins_base_url))

    try:
        jenkins    = LinaroAndroidBuildSystem(jenkins_base_url, jenkins_project, options.jenkins_user, options.jenkins_token)
        lava       = LAVA(options.lava_user, options.lava_token)
        lava.set_result_filename(options.result_file_name)
        backend_db = ArtDb(options.backend_url, options.backend_token)
        gerrit_param = jenkins.get_build_gerrit_parameters(int(jenkins_build_number))
        manifest     = jenkins.get_build_manifest(int(jenkins_build_number))
        branch       = jenkins.get_build_branch(int(jenkins_build_number))

        data = { "build_url" : options.build_url,
                 "manifest": manifest,
                 "gerrit_params": gerrit_param,
                 "branch": branch,
                 "test_result": {} }

        test_job_ids = jenkins.get_build_test_job_ids(int(jenkins_build_number))
        logger.info("Test job IDs: %s" % str(test_job_ids))
        for tid in test_job_ids:
            logger.info("Querying job #%s test results" % tid)
            try:
                data['test_result'] = lava.get_test_results(tid)
            except Exception as e:
                logger.error(e, exc_info=True)
                exit(1)

            try:
                backend_db.submit_result_to_db(data)
            except Exception as e:
                logger.error(e, exc_info=True)
                exit(1)

    except Exception as e:
        logger.error("Can not get required build information!\n%s" % e)
        logger.error(e, exc_info=True)
        exit(1)
