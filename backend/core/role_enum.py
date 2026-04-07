from enum import Enum


class UserRole(str, Enum):
    superadmin = "superadmin"   # global admin
    orgadmin = "orgadmin"       # organization-level admin
    user = "user"               # normal user
    consultant = "consultant"
    manager = "manager"
    finance = "finance"


class MessageType(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"  # For system messages like "Session started"
