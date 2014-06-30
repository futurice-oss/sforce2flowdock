"""
Helpers for using the SalesForce API.
https://developer.salesforce.com/page/REST_API

Your application should explicitly set the following variables in this module:
INSTANCE_NAME.
"""

import contextlib
import json
import logging
import requests_oauthlib
from urllib.parse import urljoin
import urllib.request


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
        with open(self._tokenFileName, 'w', encoding='utf-8') as f:
            json.dump(token, f)
        self._token = token


    def _getOAuth2Client(self):
        """
        Returns a new OAuth2Session configured from this object's settings.

        It auto-refreshes the token.
        """
        # http://requests-oauthlib.readthedocs.org/en/latest/oauth2_workflow.html#refreshing-tokens
        client = requests_oauthlib.OAuth2Session(self._config['client_id'],
                token=self._token,
                auto_refresh_url=type(self)._tokenUri,
                auto_refresh_kwargs={
                    'client_id': self._config['client_id'],
                    'client_secret': self._config['client_secret'],
                },
                token_updater=self._saveToken)
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
