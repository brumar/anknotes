import errno
from anknotes.evernote.edam.error.ttypes import EDAMErrorCode
from anknotes.logging import log_error, log, showInfo, show_tooltip


class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)


EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError
DEBUG_RAISE_API_ERRORS = False

latestSocketError = {'code': 0, 'friendly_error_msg': '', 'constant': ''}


def HandleSocketError(e, strErrorBase):
    global latestSocketError
    errorcode = e[0]
    friendly_error_msgs = {
        errno.ECONNREFUSED: "Connection was refused",
        errno.WSAECONNRESET: "Connection was reset or forcibly closed by the remote host",
        errno.ETIMEDOUT: "Connection timed out"
    }
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
    strError += "Please retry your request in {} min".format("%d:%02d" % (m, s))
    log_strError = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + strError.replace('\r\n', '\n')
    log_error(log_strError)
    log(log_strError, 'api')
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True
