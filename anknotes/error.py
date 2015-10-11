import errno
from anknotes.evernote.edam.error.ttypes import EDAMErrorCode
from anknotes.base import str_safe
from anknotes.logging import log_error, log, showInfo, show_tooltip, log_dump
from anknotes.constants import *

latestSocketError = {'code': 0, 'friendly_error_msg': '', 'constant': ''}


def HandleSocketError(e, strErrorBase):
    global latestSocketError
    errorcode = e[0]
    friendly_error_msgs = {
        errno.ECONNREFUSED:  "Connection was refused",
        errno.WSAECONNRESET: "Connection was reset or forcibly closed by the remote host",
        errno.ETIMEDOUT:     "Connection timed out"
    }
    if errorcode not in errno.errorcode:
        log_error("Unknown socket error (%s) occurred: %s" % (str(errorcode), str(e)))
        return False
    error_constant = errno.errorcode[errorcode]
    if errorcode in friendly_error_msgs:
        strError = friendly_error_msgs[errorcode]
    else:
        strError = "Unhandled socket error (%s) occurred" % error_constant
    latestSocketError = {'code': errorcode, 'friendly_error_msg': strError, 'constant': error_constant}
    strError = "Error: %s while %s\r\n" % (strError, strErrorBase)
    log_error(" SocketError.%s:  " % error_constant + strError)
    log_error(str(e))
    log(" SocketError.%s:  " % error_constant + strError, 'api')
    if EVERNOTE.API.EDAM_RATE_LIMIT_ERROR_HANDLING is EVERNOTE.API.RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EVERNOTE.API.EDAM_RATE_LIMIT_ERROR_HANDLING is EVERNOTE.API.RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True


latestEDAMRateLimit = 0


def HandleEDAMRateLimitError(e, strError):
    global latestEDAMRateLimit
    if not e.errorCode is EDAMErrorCode.RATE_LIMIT_REACHED:
        return False
    latestEDAMRateLimit = e.rateLimitDuration
    m, s = divmod(e.rateLimitDuration, 60)
    strError = "Error: Rate limit has been reached while %s\r\n" % strError
    strError += "Please retry your request in {} min".format("%d:%02d" % (m, s))
    log_strError = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + strError.replace('\r\n', '\n')
    log_error(log_strError)
    log(log_strError, 'api')
    if EVERNOTE.API.EDAM_RATE_LIMIT_ERROR_HANDLING is EVERNOTE.API.RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EVERNOTE.API.EDAM_RATE_LIMIT_ERROR_HANDLING is EVERNOTE.API.RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True


lastUnicodeError = None


def HandleUnicodeError(log_header, e, guid, title, action='', attempt=1, content=None, field=None, attempt_max=3,
                       attempt_min=1):
    global lastUnicodeError
    object = ""
    e_type = e.__class__.__name__
    is_unicode = e_type.find("Unicode") > -1
    if is_unicode:
        content_type = e.object.__class__.__name__
        object = e.object[e.start - 20:e.start + 20]
    elif not content:
        content = "Not Provided"
        content_type = "N/A"
    else:
        content_type = content.__class__.__name__
    log_header += ': ' + e_type + ': {field}' + content_type + (' <%s>' % action if action else '')
    save_header = log_header.replace('{field}', '') + ': ' + title
    log_header = log_header.format(field='%s: ' % field if field else '')

    new_error = lastUnicodeError != save_header

    if is_unicode:
        return_val = 1 if attempt < attempt_max else -1
        if new_error:
            log(save_header + '\n' + '-' * ANKNOTES.FORMATTING.LINE_LENGTH, 'unicode', replace_newline=False)
            lastUnicodeError = save_header
        log(ANKNOTES.FORMATTING.TIMESTAMP_PAD + '\t - ' + (
            ('Field %s' % field if field else 'Unknown Field') + ': ').ljust(20) + str_safe(object), 'unicode',
            timestamp=False)
    else:
        return_val = 0
        if attempt is 1 and content:
            log_dump(content, log_header, 'NonUnicodeErrors')
    if (new_error and attempt >= attempt_min) or not is_unicode:
        log_error(log_header + "\n -  Error: %s\n -   GUID: %s\n -  Title: %s%s" % (
            str(e), guid, str_safe(title), '' if not object else "\n - Object: %s" % str_safe(object)))
    return return_val
