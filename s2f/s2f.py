import json
import logging
import sys

import s2f.sforce
import s2f.flowdock


def getLogger():
    return logging.getLogger(__name__)


def fmtForChat(detail):
    """
    Format opportunity chatter details into a message string for Chat.
    """
    result = ('{opportunity_name} ' +
            '({stage}, owner {opportunity_owner}, account {account_name}) '
            ).format(**detail)

    def fmtNr(n):
        if int(n) == n:
            n = int(n)
        return '{:,}'.format(n)

    lineItems = []
    if detail['amount']:
        lineItems.append('Amount: ' + fmtNr(detail['amount']))
    if detail['probability']:
        lineItems.append('Probability: ' + fmtNr(detail['probability']))
    if detail['average_hour_price']:
        lineItems.append('Avg hour price: ' +
                fmtNr(detail['average_hour_price']))
    if detail['close_date']:
        lineItems.append('Close date: ' + detail['close_date'])
    if detail['type_of_sales']:
        lineItems.append('Type of sales: ' + detail['type_of_sales'])
    result += '\n' + ', '.join(lineItems)

    result += '\n\n' + detail['actor_name']

    if detail['text']:
        result += ' – ' + detail['text']

    return result


def fmtForTeamInbox(detail):
    """
    Format opportunity chatter details to a data structure for Team Inbox.
    """
    txt = ('Opportunity: ' +
            '{stage}, owner {opportunity_owner}, account {account_name}.'
            ).format(**detail)

    def fmtNr(n):
        if int(n) == n:
            n = int(n)
        return '{:,}'.format(n)

    lineItems = []
    if detail['amount']:
        lineItems.append('Amount ' + fmtNr(detail['amount']))
    if detail['probability']:
        lineItems.append('Probability ' + fmtNr(detail['probability']) + '%')
    if detail['average_hour_price']:
        lineItems.append('Avg. hour price ' +
                fmtNr(detail['average_hour_price']))
    if detail['close_date']:
        lineItems.append('Close date ' + detail['close_date'])
    if detail['type_of_sales']:
        lineItems.append('Type of sales: ' + detail['type_of_sales'])
    txt += '\n' + ', '.join(lineItems) + '.'

    txt += '\n\n' + detail['actor_name']
    if detail['text']:
        txt += ':\n' + detail['text']

    return {
        'teamName': detail['futu_team'],
        'subject': '{opportunity_name} – {actor_name}'.format(**detail),
        'textContent': txt,
        'project': detail['account_name'],
    }


def postNewOpportunities(sforceCfgFileName, sforceTokenFileName,
        flowdockCfgFileName, limitsFileName, startUrl=None):
    """
    Post new SalesForce Opportunities activity to Flowdock Team Inbox.

    Returns the updatesUrl to use next time to fetch only newer activity.
    """
    sClient = s2f.sforce.SClient(sforceCfgFileName, sforceTokenFileName)
    fClient = s2f.flowdock.FClient(flowdockCfgFileName)
    with open(limitsFileName, 'r', encoding='utf-8') as f:
        limits = json.load(f)

    kwArgs = {
        'maxSeconds': limits['maxSeconds'],
        'maxPages': limits['maxPages'],
        'maxTeamOpportunities': limits['maxTeamOpportunities'],
    }
    if startUrl:
        kwArgs['url'] = startUrl
    items, updatesUrl = sClient.getOpportunitiesChatterDetails(**kwArgs)
    for item in items:
        try:
            fClient.postToInbox(**fmtForTeamInbox(item))
        except:
            getLogger().error('While posting item «' + json.dumps(item) + '»:',
                    exc_info=sys.exc_info())
    return updatesUrl
