from datetime import datetime

from dynafield.fields.base_field import build_dynamic_model
from dynafield.fields.date_field import DateTimeField
from dynafield.fields.email_field import EmailField
from dynafield.fields.enum_field import EnumField
from dynafield.fields.int_field import IntField
from dynafield.fields.list_field import ListField
from dynafield.fields.object_field import ObjectField
from dynafield.fields.str_field import StrField

EvidenceItemField = ObjectField(
    label="evidenceItem",
    fields=[
        StrField(label="field"),
        StrField(label="text"),
    ],
)

booking_fields = [
    # Fixed literals
    StrField(
        label="tag",
        default_str="booking",
        description="Constant literal indicating this is a booking super tag.",
    ),
    # Booking payload
    IntField(label="numberOfGuests"),  # optional → no default
    DateTimeField(label="date"),  # optional
    StrField(label="firstName"),
    StrField(label="lastName"),
    EmailField(label="email"),
    StrField(label="phone"),
    StrField(label="specialRequest"),
    EnumField(
        label="requestType",
        allowed_values=[
            "NEW_BOOKING",
            "CHANGE_GUESTS_NUMBER",
            "CHANGE_DATE_TIME",
            "ADD_SPECIAL_REQUEST",
            "OTHER_UPDATE",
            "CANCEL_BOOKING",
        ],
        description="Type of booking request.",
    ),
    StrField(label="bookingId"),
    ListField(
        label="evidence",
        description="Items explaining why each field was set; text must be a 1:1 copy from the analyzed content.",
    ),
]

if __name__ == "__main__":
    BookingSuperTagModel = build_dynamic_model("BookingSuperTagModel", booking_fields)
    m = BookingSuperTagModel(
        requestType="NEW_BOOKING",
        numberOfGuests=4,
        date=datetime.utcnow(),
        firstName="Ada",
        lastName="Lovelace",
        email="ada@example.com",
        evidence=[{"field": "date", "text": "Tomorrow 19:00"}],
    )
