import datetime
import iso8601
import json
import logging
import pytz
import sys

import s2f.sforce
import s2f.flowdock


def getLogger():
    return logging.getLogger(__name__)


def fmtNr(n):
    if int(n) == n:
        n = int(n)
    return '{:,}'.format(n)


def fmtTimeStamp(ts, tzName):
    naive = datetime.datetime.utcfromtimestamp(ts)
    aware = pytz.utc.localize(naive)
    aware = aware.astimezone(pytz.timezone(tzName))
    timeStr = aware.strftime('%d %b %Y at %H:%M %Z')
    return timeStr


def fmtOpportunitySummary(op):
    txt = ('Stage: ' +
            '{StageName}, Owner: {OwnerName}, Account: {AccountName}.'
            ).format(**op)

    lineItems = []
    if op['Amount']:
        lineItems.append('Amount: ' + fmtNr(op['Amount']))
    if op['Probability']:
        lineItems.append('Probability: ' + fmtNr(op['Probability']) + '%')
    if op['AvgHourPrice']:
        lineItems.append('Avg. hour price: ' + fmtNr(op['AvgHourPrice']))
    if op['CloseDate']:
        lineItems.append('Close date: ' + op['CloseDate'])
    if op['TypeOfSales']:
        lineItems.append('Type of sales: ' + op['TypeOfSales'])
    if lineItems:
        txt += '\n' + ', '.join(lineItems) + '.'

    return txt


def fmtForChat(detail):
    """
    Format opportunity chatter details into a message string for Chat.
    """
    result = ('{opportunity_name} ' +
            '({stage}, owner {opportunity_owner}, account {account_name}) '
            ).format(**detail)

    lineItems = []
    if detail['amount']:
        lineItems.append('Amount: ' + fmtNr(detail['amount']))
    if detail['probability']:
        lineItems.append('Probability: ' + fmtNr(detail['probability']))
    if detail['average_hour_price']:
        lineItems.append('Avg. hour price: ' +
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


def fmtOpChatterForTeamInbox(detail, tzName):
    """
    Format opportunity chatter details to a data structure for Team Inbox.
    """
    txt = ''
    if detail['text']:
        txt += detail['text'] + '\n\n'

    timeStr = fmtTimeStamp(detail['modified_ts'], tzName)
    txt += '– ' + detail['actor_name'] + ' (' + timeStr + ')'

    txt += ('\n\nStage: ' +
            '{stage}, Owner: {opportunity_owner}, Account: {account_name}.'
            ).format(**detail)

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

    return {
        'teamName': detail['futu_team'],
        'subject': '[chatter] {opportunity_name} – {actor_name}'.format(
            **detail),
        'textContent': txt,
        'project': detail['account_name'],
    }


def fmtNewOpForTeamInbox(op, tzName):
    """
    Format new opportunity to a data structure for Team Inbox.
    """
    txt = ''
    if op['Description']:
        txt += op['Description'] + '\n\n'

    ts = int(iso8601.parse_date(op['CreatedDate']).timestamp())
    timeStr = fmtTimeStamp(ts, tzName)
    txt += '– {} created by {}'.format(timeStr, op['CreatedByName'])

    if op['LastModifiedDate'] != op['CreatedDate']:
        ts = int(iso8601.parse_date(op['LastModifiedDate']).timestamp())
        timeStr = fmtTimeStamp(ts, tzName)
        txt += '\n– {} modified by {}'.format(timeStr, op['LastModifiedByName'])

    txt += '\n\n'
    txt += fmtOpportunitySummary(op)

    return {
        'teamName': op['FutuTeam'],
        'subject': '{Name} — {CreatedByName}'.format(**op),
        'textContent': txt,
        'project': op['AccountName'],
    }


def fmtOpChangeForTeamInbox(oldOp, newOp, tzName):
    """
    Format a changed opportunity to a data structure for Team Inbox.
    """
    def snippet(text, maxLen=40):
        """
        Return text or "prefix…" if text is too long.
        """
        if maxLen < 1:
            raise ValueError('maxLen must be ≥ 1')
        if len(text) > maxLen:
            return text[:maxLen-1] + '…'
        return text

    txt = 'Updated fields:\n'
    for fName, fDisplay in s2f.sforce.OPPORTUNITY_CHANGED_FIELDS.items():
        if oldOp[fName] != newOp[fName]:
            # str(…) in case these fields aren't strings (int, None, etc)
            if fName == 'Description':
                txt += '{}: {}\n'.format(fDisplay, str(newOp[fName]))
            else:
                oldVal, newVal = oldOp[fName], newOp[fName]

                # print 50000 as 50,000; check types: we also get string, None.
                numTypes = {int, float}
                if type(oldVal) in numTypes:
                    oldVal = fmtNr(oldVal)
                if type(newVal) in numTypes:
                    newVal = fmtNr(newVal)

                txt += '{}: {} → {}\n'.format(fDisplay,
                        snippet(str(oldVal)), snippet(str(newVal)))

    ts = int(iso8601.parse_date(newOp['LastModifiedDate']).timestamp())
    timeStr = fmtTimeStamp(ts, tzName)
    txt += '\n– {} modified by {}'.format(timeStr, newOp['LastModifiedByName'])

    txt += '\n\n'
    txt += fmtOpportunitySummary(newOp)

    return {
        'teamName': newOp['FutuTeam'],
        'subject': '[updated] {Name} — {LastModifiedByName}'.format(**newOp),
        'textContent': txt,
        'project': newOp['AccountName'],
    }


def postNewAndModifiedOpportunities(sClient, fClient, limits,
        opportunitiesFileName):
    """
    Post new and modified opportunities to Team Inbox.
    """
    skipFlowdock = False
    try:
        with open(opportunitiesFileName, 'r', encoding='utf-8') as f:
            knownOps = json.load(f)
    except (FileNotFoundError, ValueError):
        # likely first run (missing or invalid file). Save file but don't post.
        skipFlowdock = True
        knownOps = []
        getLogger().warn('While reading opportunities file:',
                exc_info=sys.exc_info())
    knownOps = {op['Id']:op for op in knownOps}

    allOps, newOps, changedOps = sClient.getOpportunityChanges(knownOps,
            maxTeamItems = limits['maxTeamOpportunities'])
    try:
        with open(opportunitiesFileName, 'w', encoding='utf-8') as f:
            json.dump(allOps, f)
    except:
        getLogger().error('While saving opportunities file:',
                exc_info=sys.exc_info())

    if skipFlowdock:
        return

    for op in newOps:
        try:
            fClient.postToInbox(**fmtNewOpForTeamInbox(op,
                fClient.getTeamTzName(op['FutuTeam'])))
        except:
            getLogger().error('While posting new opportunity «' +
                    json.dumps(op) + '»:', exc_info=sys.exc_info())

    for newOp in changedOps:
        opId = newOp['Id']
        if opId not in knownOps:
            getLogger().warn('Changed Opportunity ID ' + opId +
                ' not in old opportunities')
            continue
        oldOp = knownOps[opId]
        try:
            fClient.postToInbox(**fmtOpChangeForTeamInbox(oldOp, newOp,
                fClient.getTeamTzName(newOp['FutuTeam'])))
        except:
            getLogger().error('While posting changed opportunity «' +
                    json.dumps(newOp) + '»:', exc_info=sys.exc_info())


def postOpportunitiesChatter(sClient, fClient, limits, startUrl=None):
    """
    Post opportunities chatter to Team Inbox and return the updatesUrl.
    """
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
            fClient.postToInbox(**fmtOpChatterForTeamInbox(item,
                fClient.getTeamTzName(item['futu_team'])))
        except:
            getLogger().error('While posting item «' + json.dumps(item) + '»:',
                    exc_info=sys.exc_info())
    return updatesUrl


def postNewActivity(sforceCfgFileName, sforceTokenFileName,
        flowdockCfgFileName, limitsFileName, opportunitiesFileName,
        startUrl=None):
    """
    Post new SalesForce Opportunities activity to Flowdock Team Inbox.

    Returns the updatesUrl to use next time to fetch only newer activity.
    """
    sClient = s2f.sforce.SClient(sforceCfgFileName, sforceTokenFileName)
    fClient = s2f.flowdock.FClient(flowdockCfgFileName)
    with open(limitsFileName, 'r', encoding='utf-8') as f:
        limits = json.load(f)

    postNewAndModifiedOpportunities(sClient, fClient, limits,
            opportunitiesFileName)

    return postOpportunitiesChatter(sClient, fClient, limits,
            startUrl=startUrl)
