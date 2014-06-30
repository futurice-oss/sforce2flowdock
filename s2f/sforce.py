"""
Helpers for using the SalesForce API.
https://developer.salesforce.com/page/REST_API

Your application should explicitly set the following variables in this module:
INSTANCE_NAME.
"""

import json
from urllib.parse import urljoin
import urllib.request


class SClient():
    """
    Class which takes basic configuration and makes SalesForce API calls.

    Most methods require you to have already set the following instance fields:
    apiInstanceName, apiPath.

    Methods which don't need all the above fields set (e.g. getAPIVersions())
    mention this in their docstring.

    Instance Fields:
    apiInstanceName - the SalesForce server to connect to, e.g. 'na1', 'eu1'.
                    Produces https://‹apiInstanceName›.salesforce.com/…
    apiPath - the root path of the API version you are using, e.g.
            '/services/data/v31.0'. Use getAPIVersions() to list all current
            versions and their URLs.
    """

    def __init__(self):
        self.apiInstanceName = None
        self.apiPath = None


    def _getApiHost(self):
        return self.apiInstanceName + '.salesforce.com'

    def _getHostUrl(self):
        return 'https://' + self._getApiHost() + '/'


    def getAPIVersions(self):
        """
        Returns the parsed JSON listing current API versions.

        Only requires that you set the apiInstanceName field.
        """
        url = urljoin(self._getHostUrl(), '/services/data/')
        req = urllib.request.urlopen(url)
        return json.loads(req.read().decode('utf-8'))
