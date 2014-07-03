import json
import logging
import sys

import s2f.sforce
import s2f.flowdock


def getLogger():
    return logging.getLogger(__name__)


def formatOpChatterDetail(detail):
    """
    Format opportunity chatter details into a message string.
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

    line = ''
    if line:
        result += '\n' + line

    result += '\n\n' + detail['actor_name']

    if detail['text']:
        result += ' – ' + detail['text']

    return result


def postNewOpportunities(sforceCfgFileName, sforceTokenFileName,
        flowdockCfgFileName, limitsFileName, startUrl=None):
    """
    Post new SalesForce Opportunities activity to Flowdock Chat.

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
            msg = formatOpChatterDetail(item)
            fClient.chat(item['futu_team'], msg)
        except:
            getLogger().error('While posting item «' + json.dumps(item) + '»:',
                    exc_info=sys.exc_info())
    return updatesUrl
