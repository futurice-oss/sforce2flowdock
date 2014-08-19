"""
Helpers for using the SalesForce API.
https://developer.salesforce.com/page/REST_API
"""

from collections import OrderedDict
import contextlib
import datetime
import iso8601
import json
import logging
import requests_oauthlib
from urllib.parse import urljoin
import urllib.request

from s2f import util


def getLogger():
    return logging.getLogger(__name__)


# Opportunity fields which, if changed, indicate an opportunity modification.
# This dictionary maps the field names to printable labels.
OPPORTUNITY_CHANGED_FIELDS = OrderedDict((
    ('Name', 'Name'),
    ('Description', 'Description'),
    ('AccountName', 'Account'),
    ('OwnerName', 'Owner'),
    ('StageName', 'Stage'),
    ('Amount', 'Amount'),
    ('Probability', 'Probability'),
    ('CloseDate', 'Close date'),
    ('TypeOfSales', 'Type of sales'),
    ('AvgHourPrice', 'Avg. hour price'),
    ('FutuTeam', 'Tribe'),
    ('IsClosed', 'Closed'),
    ('IsWon', 'Won'),
))


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


    def getJson(self, url, params=None):
        """
        Returns the JSON from url. If relative, it's relative to the API Root.

        Use this to test & explore the API.
        """
        client = self._getOAuth2Client()
        url = urljoin(self._getAPIRootUrl(), url)
        return client.get(url, params=params).json()


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


    def getCompanyChatter(self, url='chatter/feeds/company/feed-items',
            maxSeconds=60*60*24*31, maxFeedItems=100, maxPages=5,
            hardLimit=False):
        """
        Get chatter items and updatesUrl, stopping when any limits are reached.

        The URL parameter may be overriden, e.g. with an ‘updatesUrl’
        previously returned by the API.
        Stop if we reach the end or found items older than maxSeconds, or found
        maxFeedItems or got maxPages of results.
        If hardLimit is True, drop any retrieved results which exceed these
        limits, otherwise keep them.
        """
        now = datetime.datetime.now().timestamp()
        items = []
        maxSecsExceeded = False
        pagesRetrieved = 0
        updatesUrl = None

        client = self._getOAuth2Client()
        while (url and not maxSecsExceeded and len(items) < maxFeedItems and
                pagesRetrieved < maxPages):
            url = urljoin(self._getAPIRootUrl(), url)
            data = client.get(url).json()
            if pagesRetrieved == 0:
                updatesUrl = data['updatesUrl']

            pagesRetrieved += 1
            for item in data['items']:
                if hardLimit and len(items) >= maxFeedItems:
                    break
                then = iso8601.parse_date(item['modifiedDate']).timestamp()
                if now - then > maxSeconds:
                    maxSecsExceeded = True
                if hardLimit and maxSecsExceeded:
                    break
                items.append(item)

            url = data['nextPageUrl']

        return items, updatesUrl


    def getOpportunitiesChatter(self, *args, maxOpportunities=None, **kwargs):
        """
        Filter getCompanyChatter() results to opportunities & updatesUrl

        If maxOpportunities is given, only that number of items are kept after
        filtering.
        Forwards all its other arguments to getCompanyChatter().
        """
        result, updatesUrl = self.getCompanyChatter(*args, **kwargs)
        result = [x for x in result if
                util.getNested(x, 'parent.type') == 'Opportunity']
        if maxOpportunities is not None:
            result = result[:maxOpportunities]
        return result, updatesUrl


    def getOpportunitiesChatterDetails(self, *args, maxTeamOpportunities=None,
            **kwargs):
        """
        Return custom data structures for the Opportunities chatter & updatesUrl

        If maxTeamOpportunities is given, keeps only so many opportunities for
        each Futu_Team.
        Pass all other arguments to getOpportunitiesChatter(). Get additional
        objects from the API (e.g. Opportunities, Accounts, Users).
        Return a list of objects with information to display, one object for
        each item in the opportunities chatter.
        """
        getLogger().info('Getting SalesForce opportunities chatter')
        opChatter, updatesUrl = self.getOpportunitiesChatter(*args, **kwargs)

        def getSetOfNestedValues(srcIter, path):
            """
            Return a set with all truthy values at path in srcIter
            """
            result = set()
            for s in srcIter:
                v = util.getNested(s, path)
                if v:
                    result.add(v)
            return result

        ns = util.getNested
        opportunityIds = getSetOfNestedValues(opChatter, 'parent.id')
        getLogger().info('Getting {} SalesForce Opportunity objects'.format(
            len(opportunityIds)))
        oppById = {x:self.getOpportunity(x) for x in opportunityIds}

        if maxTeamOpportunities is not None:
            opCountForTeam = {}
            def filterFunc(oc):
                opp = ns(oppById, ns(oc, 'parent.id'))
                if not opp:
                    return False
                team = ns(opp, 'Futu_Team__c', '')
                opCountForTeam[team] = 1 + (opCountForTeam[team]
                        if team in opCountForTeam else 0)
                return opCountForTeam[team] <= maxTeamOpportunities
            opChatter = list(filter(filterFunc, opChatter))

        # filter the opportunity objects
        opportunityIds = getSetOfNestedValues(opChatter, 'parent.id')
        oppById = {x:oppById[x] for x in opportunityIds}

        accountIds = getSetOfNestedValues(oppById.values(), 'AccountId')
        getLogger().info('Getting {} SalesForce Accounts'.format(
            len(accountIds)))
        accById = {x:self.getAccount(x) for x in accountIds}

        userIds = getSetOfNestedValues(oppById.values(), 'OwnerId')
        getLogger().info('Getting {} SalesForce Users'.format(len(userIds)))
        usersById = {x:self.getUser(x) for x in userIds}

        def customData(opC):
            """
            Create a custom data structure for an opportunity chatter item.
            """
            opp = ns(oppById, ns(opC, 'parent.id', ''))
            # If the nested fields have a value of None, we return None to the
            # caller. But if the fiels don't exist, the SalesForce data
            # structure is different than what we expect, so we return these
            # truthy warning strings.
            return {
                'opportunity_name': ns(opp, 'Name', 'Unknown Opportunity'),
                'account_name': ns(accById,
                    ns(opp, 'AccountId', '') + '.Name', 'Unknown Account'),
                'opportunity_owner': ns(usersById,
                    ns(opp, 'OwnerId', '') + '.Name', 'Unknown Owner'),
                'stage': ns(opp, 'StageName', '¡Missing! StageName'),
                'amount': ns(opp, 'Amount', '¡Missing! Amount'),
                'probability': ns(opp, 'Probability', '¡Missing! Probability'),
                'close_date': ns(opp, 'CloseDate', '¡Missing! CloseDate'),
                'type_of_sales': ns(opp, 'Type_of_Sales__c',
                    '¡Missing! Type_of_Sales__c'),
                'average_hour_price': ns(opp, 'Average_Hour_Price__c',
                    '¡Missing! Average_Hour_Price__c'),
                'futu_team': ns(opp, 'Futu_Team__c', '¡Missing! Futu_Team__c'),

                # not sure if the body.text is always present, so not reporting
                # it with a warning string.
                'text': ns(opC, 'body.text'),
                'modified_ts': int(iso8601.parse_date(
                    ns(opC, 'modifiedDate', 0)).timestamp()),
                'actor_name': ns(opC, 'actor.name', '¡Missing! actor.name'),
                'type': ns(opC, 'type', '¡Missing! type'),
                'preamble_text': ns(opC, 'preamble.text',
                    '¡Missing! preamble.text'),
            }

        return [customData(x) for x in opChatter], updatesUrl


    def getOpportunity(self, ID):
        return self.getJson('sobjects/Opportunity/' + ID)

    def getAccount(self, ID):
        return self.getJson('sobjects/Account/' + ID)

    def getUser(self, ID):
        return self.getJson('sobjects/User/' + ID)

    def getOpportunities(self, minModified=None):
        """
        Get all Opportunities, reverse sorted by modified time.

        If minModified is not None, only get Opportunities modified at or after
        this time.
        """
        fields = (
            'Id',
            'Name',
            'Description',
            'Account.Name',
            'Owner.Name',
            'StageName',
            'Amount',
            'Probability',
            'CloseDate',
            'Type_of_Sales__c',
            'Average_Hour_Price__c',
            'Futu_Team__c',

            'IsClosed',
            'IsWon',

            'CreatedDate',
            'CreatedBy.Name',
            'LastModifiedDate',
            'LastModifiedBy.Name',
        )
        q = 'SELECT ' + ','.join(fields) + ' FROM Opportunity'
        if minModified:
            q += ' WHERE LastModifiedDate >= ' + minModified
        q += ' ORDER BY LastModifiedDate DESC'
        resp = self.getJson('query/', params={'q': q})
        results = resp['records']

        while 'nextRecordsUrl' in resp and resp['nextRecordsUrl']:
            # Can't test this – we get all the results in one call.
            # But the docs describe this ‘next…’ field.
            resp = self.getJson(resp['nextRecordsUrl'])
            results.extend(resp['records'])

        def fmtObj(x):
            return {
                'Id':           x['Id'],
                'Name':         x['Name'],
                'Description':  x['Description'],
                'AccountName':  x['Account']['Name'],
                'OwnerName':    x['Owner']['Name'],
                'StageName':    x['StageName'],
                'Amount':       x['Amount'],
                'Probability':  x['Probability'],
                'CloseDate':    x['CloseDate'],
                'TypeOfSales':  x['Type_of_Sales__c'],
                'AvgHourPrice': x['Average_Hour_Price__c'],
                'FutuTeam':     x['Futu_Team__c'],
                'IsClosed':     x['IsClosed'],
                'IsWon':        x['IsWon'],

                'CreatedDate':  x['CreatedDate'],
                'CreatedByName':    x['CreatedBy']['Name'],
                'LastModifiedDate': x['LastModifiedDate'],
                'LastModifiedByName':   x['LastModifiedBy']['Name'],
            }
        return [fmtObj(r) for r in results]

    def getOpportunityChanges(self, knownOpsSet, maxTeamItems):
        """
        Return allOps, newOps, changedOps.

        newOps and changedOps together have at most maxTeamItems for each team.
        """
        latestModified, latestModifiedTs = None, 0
        for op in knownOpsSet.values():
            opTs = iso8601.parse_date(op['LastModifiedDate']).timestamp()
            if opTs > latestModifiedTs:
                latestModified = op['LastModifiedDate']
                latestModifiedTs = opTs
        incoming = self.getOpportunities(minModified=latestModified)

        ns = util.getNested
        def opHasChanged(v1, v2):
            for f in OPPORTUNITY_CHANGED_FIELDS.keys():
                if ns(v1, f) != ns(v2, f):
                    return True
            return False

        # don't modify the caller's object, copy it
        allOps = {k:v for k, v in knownOpsSet.items()}
        newOps, changedOps = [], []
        teamOps = {}
        for op in incoming:
            opId = op['Id']
            team = op['FutuTeam']

            if teamOps.get(team, 0) < maxTeamItems:
                if opId not in allOps:
                    teamOps[team] = teamOps.get(team, 0) + 1
                    newOps.append(op)
                elif opHasChanged(allOps[opId], op):
                    teamOps[team] = teamOps.get(team, 0) + 1
                    changedOps.append(op)

            allOps[opId] = op

        return list(allOps.values()), newOps, changedOps
