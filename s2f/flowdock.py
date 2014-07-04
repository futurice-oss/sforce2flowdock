import html
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
    externalUserName should contain no spaces or Flowdock will return an error,
    and it looks like it should be 16 characters or less.
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


def postToInbox(flowApiToken, source, from_address, subject, textContent,
        from_name=None, project=None, tags=[], link=None):
    """
    Post a message to a flow's Team Inbox, escaping textContent to valid HTML.

    https://www.flowdock.com/api/team-inbox
    textContent is escaped to valid HTML and newlines are replaced with <br>.
    The API call may throw exceptions.
    """
    htmlContent = html.escape(textContent).replace('\n', '<br>')
    url = ('https://api.flowdock.com/v1/messages/team_inbox/' +
            urllib.parse.quote(flowApiToken))

    data = {
        # required fields
        'source': source,
        'from_address': from_address,
        'subject': subject,
        'content': htmlContent,
        # optional fields
        'format': 'html',
        'tags': tags
    }
    if from_name:
        data['from_name'] = from_name
    if project:
        data['project'] = project
    if link:
        data['link'] = link
    data = json.dumps(data).encode('utf-8')

    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
    }
    req = urllib.request.Request(url, data, headers)
    getLogger().info('Posting message to Team Inbox: ' + data.decode('utf-8'))
    urllib.request.urlopen(req)


class FClient():
    """
    Flowdock API client.

    Initialized with a configuration file which contains, among other things,
    a mapping from the Futu_Team name to the secret API Token for a Flowdock
    channel. You can define an optional default flow for messages with an
    unknown team name.
    """

    def __init__(self, cfgFileName):
        with open(cfgFileName, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.flowForTeam = data['flowForTeam']
        self.defaultFlow = util.getNested(data, 'defaultFlow')

        self.teamInbox = data['teamInbox']


    def postToInbox(self, teamName, subject, textContent, project=None,
            link=None):
        """
        Posts to the Team Inbox.

        May throw exceptions.
        """
        if teamName in self.flowForTeam:
            apiToken = self.flowForTeam[teamName]
        elif self.defaultFlow:
            getLogger().warn('Unknown Team: ' + teamName + ', posting chat ' +
                    'to default flow')
            apiToken = self.defaultFlow
        else:
            getLogger().warn('Unknown Team: ' + teamName + ' and no default ' +
                    'flow configured')
            return

        postToInbox(apiToken, self.teamInbox['source'],
                self.teamInbox['from_address'], subject, textContent,
                self.teamInbox['from_name'], project, self.teamInbox['tags'],
                link)
