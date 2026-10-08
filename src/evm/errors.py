class RPCError(Exception):
    pass


class MalformedRpcResponseError(Exception):
    pass


class WrongNetworkError(Exception):
    pass


class TransactionTrackingTimeoutError(Exception):
    pass


class TransactionRevertedError(Exception):
    pass
