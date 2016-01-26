import requests
import xmlrpclib
from optparse import OptionParser

class LavaServerException(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return repr(self.name)


class LavaServer(object):
    XMLRPC = 'RPC2/'
    BUNDLESTREAMS = 'dashboard/streams'
    JOB = 'scheduler/job'
    def __init__(self, base_url, username=None, password=None):
        self.url = base_url
        self.username = username # API username
        self.password = password # API token
        self.xmlrpc_url = base_url + LavaTestSystem.XMLRPC


    def call_xmlrpc(self, method_name, *method_params):
        payload = xmlrpclib.dumps((method_params), method_name)

        response = requests.request('POST', self.xmlrpc_url,
                                    data = payload,
                                    headers = {'Content-Type': 'application/xml'},
                                    auth = (self.username, self.password),
                                    timeout = 100,
                                    stream = False)

        if response.status_code == 200:
            result = xmlrpclib.loads(response.content)[0][0]
            return result
        else:
            raise LavaServerException(response.status_code)

    def cancel_job(self, job_id):
        return self.call_xmlrpc("scheduler.cancel_job", job_id)


if __name__ == '__main__':
    parser          = OptionParser()
    parser.add_option("--lava-url", dest="lava_url",
                        help="Specify the LAVA URL.",
                        default="https://validation.linaro.org/")
    parser.add_option("--lava-user", dest="lava_user",
                        help="Specify the LAVA user. This is MANDATORY.")
    parser.add_option("--lava-token", dest="lava_token",
                        help="Specify the LAVA token. This is MANDATORY.")
    parser.add_option("--lava-job-id", dest="lava_job_id",
                        help="Specify the LAVA job ID to cancel. This is MANDATORY.")

    options, args = parser.parse_args()

    if not options.lava_user:
        parser.error("LAVA user is mandatory")
    if not options.lava_token:
        parser.error("LAVA token is mandatory")
    if not options.lava_job_id:
        parser.error("LAVA job ID is mandatory")

    lava = LavaServer(options.lava_url, options.lava_user, options.lava_token)
    lava.cancel_job(options.lava_job_id)

