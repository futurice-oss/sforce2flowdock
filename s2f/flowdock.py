import json
import logging
import urllib.request
import urllib.parse

from s2f import util


def getLogger():
    return logging.getLogger(__name__)


def chat(flowApiToken, externalUserName, content, tags=[]):
    """
    Post a message to a flow's chat from an "external user".

    https://www.flowdock.com/api/chat
    externalUserName should contain no spaces or Flowdock will return an error.
    tags are optional additional tags; the message content is automatically
    parsed for tags.

    The API call may throw exceptions.
    """
    url = ('https://api.flowdock.com/v1/messages/chat/' +
            urllib.parse.quote(flowApiToken))
    data = json.dumps({
        'external_user_name': externalUserName,
        'content': content,
        'tags': tags,
    }).encode('utf-8')
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
    }
    req = urllib.request.Request(url, data, headers)
    getLogger().info('Posting chat message: ' + content)
    urllib.request.urlopen(req)


class FClient():
    """
    Flowdock API client.

    Initialized with a configuration file (e.g. external user name, tags,
    a prefix for each message, a mapping from the Futu_Team name to the secret
    API Token for a Flowdock channel. You can define an optional default flow
    for messages with an unknown team name, and an optional prefix string for
    those messages.
    """

    def __init__(self, cfgFileName):
        with open(cfgFileName, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.prefix = data['prefix']
        self.flowForTeam = data['flowForTeam']
        self.externalUserName = data['externalUserName']
        self.tags = data['tags']

        self.defaultFlow = util.getNested(data, 'defaultFlow')
        self.defaultFlowPrefix = util.getNested(data, 'defaultFlowPrefix',
                self.prefix)


    def chat(self, teamName, message):
        """
        Posts the chat message.

        May throw exceptions.
        """
        if teamName in self.flowForTeam:
            apiToken = self.flowForTeam[teamName]
            prefix = self.prefix
        elif self.defaultFlow:
            getLogger().warn('Unknown Team: ' + teamName + ', posting chat ' +
                    'to default flow')
            apiToken = self.defaultFlow
            prefix = self.defaultFlowPrefix or self.prefix
        else:
            getLogger().warn('Unknown Team: ' + teamName + ' and no default ' +
                    'flow configured')
            return

        if prefix:
            prefix = prefix + ' '
        message = prefix + message
        chat(apiToken, self.externalUserName, message, self.tags)
