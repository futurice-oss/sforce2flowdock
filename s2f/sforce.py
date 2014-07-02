"""
Helpers for using the SalesForce API.
https://developer.salesforce.com/page/REST_API

Your application should explicitly set the following variables in this module:
INSTANCE_NAME.
"""

import contextlib
import datetime
import dateutil.parser
import json
import logging
import requests_oauthlib
from urllib.parse import urljoin
import urllib.request

from s2f import util


def getLogger():
    return logging.getLogger(__name__)


class SClient():
    """
    Makes SalesForce API calls using the given configuration.
    """

    _authUri = 'https://login.salesforce.com/services/oauth2/authorize'
    _tokenUri = 'https://login.salesforce.com/services/oauth2/token'
    _scopes = ['chatter_api', 'api', 'refresh_token']


    def __init__(self, cfgFileName, tokenFileName):
        """
        cfgFileName - JSON file, see README.
        tokenFileName - JSON file, stores the OAuth2 Token.

        If the tokenFileName doesn't exist or has no token, the OAuth2
        authentication flow is started. This prints an authentication URL
        on the command line and asks you to type a response code.

        The token is automatically refreshed when it expires.
        """

        with open(cfgFileName, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
        self._tokenFileName = tokenFileName
        self._ensureToken()


    def _ensureToken(self):
        """
        Checks for a token in the file and start the OAuth2 flow if missing.
        """
        try:
            with open(self._tokenFileName, 'r', encoding='utf-8') as f:
                # Update this field whenever we get a new token:
                # either the user does the OAuth2 flow or we refresh the token.
                self._token = json.load(f)

                # may raise KeyError
                if not self._token['access_token']:
                    raise IOError('Empty access token')
        except (IOError, KeyError):
            getLogger().info('Missing OAuth2 token', exc_info=True)
            self._doOAuth2Flow()


    def _doOAuth2Flow(self):
        """
        Prints an auth url and waits for a code at stdin.
        """
        getLogger().info('Starting OAuth2 flow')
        # http://requests-oauthlib.readthedocs.org/en/latest/oauth2_workflow.html#web-application-flow
        client = requests_oauthlib.OAuth2Session(self._config['client_id'],
                redirect_uri=self._config['redirect_uri'],
                scope=type(self)._scopes)
        authUrl, state = client.authorization_url(type(self)._authUri)

        print()
        print(authUrl)
        print()
        print('Go to the URL above and authorize the app. ' +
                'You will be redirected to ' + self._config['redirect_uri'] +
                ' with a &code=… in the url.')
        code = input('Enter the code: ')

        token = client.fetch_token(type(self)._tokenUri,
                client_secret=self._config['client_secret'], code=code)
        self._saveToken(token)
        getLogger().info('OAuth2 flow completed successfully')


    def _saveToken(self, token):
        """
        Writes the new token to the file and updates this instance's field.
        """
        getLogger().info('Saving OAuth2 Token')
        with open(self._tokenFileName, 'w', encoding='utf-8') as f:
            json.dump(token, f)
        self._token = token


    def _getOAuth2Client(self):
        """
        Returns a new OAuth2Session configured from this object's settings.

        It auto-refreshes the token and saves it.
        """
        # http://requests-oauthlib.readthedocs.org/en/latest/oauth2_workflow.html#refreshing-tokens
        client = requests_oauthlib.OAuth2Session(self._config['client_id'],
                token=self._token)

        def refreshAndSaveToken():
            getLogger().info('Refreshing SalesForce access token')
            refresh_url = type(self)._tokenUri
            refresh_kwargs = {
                'client_id': self._config['client_id'],
                'client_secret': self._config['client_secret'],
            }
            token = client.refresh_token(refresh_url, **refresh_kwargs)
            self._saveToken(token)

        origRequest = client.request

        def autoRefreshingRequest(*args, **kwargs):
            """
            Replace the client's .request(…) method with one that
            auto-refreshes to token.

            The library says the OAuth2 protocol doesn't distinguish failures
            caused by an expired access token from other failures (e.g. by a
            special HTTP code).

            The library gives some support, including auto-refreshing the token
            for us. It does this by checking the expiration time before making
            a request (this is a potential race condition → the remote server
            may still think the token is expired even if we don't). In
            addition, SalesForce doesn't return the expires_{in|at} field with
            the token, so the mechanism can't work.

            Here, we check the SalesForce response (HTTP status code and JSON
            body) after each request. If SalesForce says the token is expired,
            we refresh the token and perform the same request again.
            """
            result = origRequest(*args, **kwargs)

            # If the token is expired, refresh it and do the request again
            if result.status_code == 401:
                try:
                    j = result.json()
                except ValueError:
                    pass
                else:
                    if type(j) == list and len(j):
                        j = j[0]
                        if (type(j) == dict and 'errorCode' in j and
                                j['errorCode'] == 'INVALID_SESSION_ID'):
                            refreshAndSaveToken()
                            result = origRequest(*args, **kwargs)

            return result

        client.request = autoRefreshingRequest
        return client


    def _getInstanceUrl(self):
        return self._token['instance_url']


    def getAPIVersions(self):
        """
        Returns the parsed JSON listing current API versions.

        This doesn't need authentication to run, but because it still needs
        an instance to connect to, it benefits from the contructor enforcing
        getting a token (thes instance url in returned with the token).
        Also keeps the design simpler to guarantee a token from the contructor.
        """
        client = self._getOAuth2Client()
        url = urljoin(self._getInstanceUrl(), '/services/data/')
        req = urllib.request.urlopen(url)
        return json.loads(req.read().decode('utf-8'))


    def _getAPIRootUrl(self):
        url = urljoin(self._getInstanceUrl(), self._config['apiVersionUrl'])
        if not url.endswith('/'):
            url = url + '/'
        return url


    def getJson(self, url):
        """
        Returns the JSON from url. If relative, it's relative to the API Root.

        Use this to test & explore the API.
        """
        client = self._getOAuth2Client()
        url = urljoin(self._getAPIRootUrl(), url)
        return client.get(url).json()


    def getAvailableResources(self):
        """
        List the available API Resources.
        """
        client = self._getOAuth2Client()
        url = self._getAPIRootUrl()
        # Still getting a ResourceWarning: unclosed ssl.SSLSocket when running
        # the tests. This is probably because of a ‘connection pool’ in the
        # ‘requests’ library, and we probably shouldn't manually close here.
        with contextlib.closing(client.get(url)) as resp:
            return resp.json()


    def getCompanyChatter(self, maxSecs=60*60*24*31, maxItems=100, maxPages=5,
            url='chatter/feeds/company/feed-items'):
        """
        Get chatter items from url, stopping when any of the limits is reached.

        Stop if we reach the end or found items older than maxSecs, or found
        more than maxItems or got more than maxPages of results.
        The URL parameter may be overriden, e.g. with an ‘updatesUrl’
        previously returned by the API.
        """
        items = []
        maxSecsExceeded = False
        pagesRetrieved = 0

        client = self._getOAuth2Client()
        while (url and not maxSecsExceeded and len(items) < maxItems and
                pagesRetrieved < maxPages):
            url = urljoin(self._getAPIRootUrl(), url)
            data = client.get(url).json()
            if pagesRetrieved == 0:
                getLogger().info('Future updates at ' + data['updatesUrl'])

            pagesRetrieved += 1
            items.extend(data['items'])
            if len(items):
                now = datetime.datetime.now().timestamp()
                for fName in ['createdDate', 'modifiedDate']:
                    then = dateutil.parser.parse(items[-1][fName]).timestamp()
                    if now - then > maxSecs:
                        maxSecsExceeded = True
                        break

            url = data['nextPageUrl']

        return items


    def getOpportunitiesChatter(self, *args, **kwargs):
        """
        Filter getCompanyChatter() results to opportunities.

        Forwards all its arguments to getCompanyChatter().
        """
        return list(filter(
            lambda x: util.getNested(x, 'parent.type') == 'Opportunity',
            self.getCompanyChatter(*args, **kwargs)))
