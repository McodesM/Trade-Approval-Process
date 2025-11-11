from django.db import models
class Direction(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"


class TradeState(models.TextChoices):
    DRAFT = "Draft", "Draft"
    PENDING_APPROVAL = "PendingApproval", "Pending Approval"
    NEEDS_REAPPROVAL = "NeedsReapproval", "Needs Reapproval"
    APPROVED = "Approved", "Approved"
    SENT_TO_COUNTERPARTY = "SentToCounterparty", "Sent To Counterparty"
    EXECUTED = "Executed", "Executed"
    CANCELLED = "Cancelled", "Cancelled"


class Action(models.TextChoices):
    SUBMIT = "Submit", "Submit"
    APPROVE = "Approve", "Approve"
    CANCEL = "Cancel", "Cancel"
    UPDATE = "Update", "Update"
    SEND_TO_EXECUTE = "SendToExecute", "Send To Execute"
    BOOK = "Book", "Book"