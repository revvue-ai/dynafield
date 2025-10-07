import uuid

from uuid_utils import uuid7


def uuid_7() -> uuid.UUID:
    # Note: Not part of standard python will be added at python 3.14. Using this for now as primary key
    return uuid.UUID(str(uuid7()))
