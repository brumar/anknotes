import errno
from anknotes.evernote.edam.error.ttypes import EDAMErrorCode
from anknotes.logging import log_error, log, showInfo, show_tooltip


class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)


EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError
DEBUG_RAISE_API_ERRORS = False

def HandleSocketError(e, strError):
    errorcode = e[0]
    if errorcode==errno.ECONNREFUSED:
        strError = "Error: Connection was refused while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ECONNREFUSED'
    elif errorcode==10060:
        strError = "Error: Connection timed out while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ETIMEDOUT'
    else: return False
    log_error( " SocketError.%s:  "  % log_prefix + strError)
    log( " SocketError.%s:  "  % log_prefix + strError, 'api')
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
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
    strError += "Please retry your request in {} min".format("%d:%02d" %(m, s))
    log_strError = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + strError.replace('\r\n', '\n')
    log_error(log_strError)
    log(log_strError, 'api')
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True