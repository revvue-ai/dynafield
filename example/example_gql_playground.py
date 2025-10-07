# -- Mutate a record schema
"""
mutation muateRecordSchema($id: String!, $name: String, $fieldDefinitions: JSON) {
  recordSchema(
    schemaToAdd: {id: $id, name: $name, fieldDefinitions: $fieldDefinitions}
  ) {
    count
  }
}
"""

# ---- values
"""
{
  "id": "0199c0c1-816d-7233-988e-cb355508bef1",
  "name": "customerField",
  "fieldDefinitions": [
    {
      "label": "tag",
      "description": "Constant literal indicating this is a booking super tag.",
      "default_str": "booking",
      "__typename": "StringField"
    },
    {
      "label": "numberOfGuests",
      "__typename": "IntField"
    },
    {
      "label": "date",
      "__typename": "DateTimeField"
    },
    {
      "label": "firstName",
      "__typename": "StringField"
    },
    {
      "label": "lastName",
      "__typename": "StringField"
    },
    {
      "label": "email",
      "__typename": "EmailField"
    },
    {
      "label": "phone",
      "__typename": "StringField"
    },
    {
      "label": "specialRequest",
      "__typename": "StringField"
    },
    {
      "label": "requestType",
      "description": "Type of booking request.",
      "allowed_values": [
        "NEW_BOOKING",
        "CHANGE_GUESTS_NUMBER",
        "CHANGE_DATE_TIME",
        "ADD_SPECIAL_REQUEST",
        "OTHER_UPDATE",
        "CANCEL_BOOKING"
      ],
      "__typename": "EnumField"
    },
    {
      "label": "bookingId",
      "__typename": "StringField"
    },
    {
      "label": "evidence",
      "description": "Items explaining why each field was set; text must be a 1:1 copy from the analyzed content.",
      "default_list": [],
      "__typename": "ListField"
    }
    ]
}
"""

# -- Mutate a record
"""
mutation mutateRecord($recordSchemaId: UUID!, $records: JSON!) {
  records(recordSchemaId: $recordSchemaId, records: $records) {
    count
    records
  }
}
"""

# ---- values
"""
{
  "recordSchemaId": "0199c0c1-816d-7233-988e-cb355508bef1",
  "records": [{"requestType": "NEW_BOOKING", "numberOfGuests": 4, "date": "2025-01-01T00:00:00", "firstName": "Ada", "lastName": "Lovelace", "email": "ada@example.com", "evidence": [{"field": "date", "text": "Tomorrow 19:00"}]}]
}
"""


# -- query record schema
"""
query recordSchema{
  recordSchema(recordSchemaId: "0199c0c1-816d-7233-988e-cb355508bef1") {
    count
    schemas {
      id
      name
      description
      fieldDefinitions {
        ...BoolFieldDefinition
        ...DateFieldDefinition
        ...DateTimeFieldDefinition
        ...EmailFieldDefinition
        ...EnumFieldDefinition
        ...FloatFieldDefinition
        ...IntFieldDefinition
        ...JsonFieldDefinition
        ...ListFieldDefinition
        ...StrFieldDefinition
        ...UuidFieldDefinition
        ...ObjectFieldDefinition
      }
    }
  }
}

fragment BoolFieldDefinition on BoolFieldGql {
  id
  label
  description
  defaultBool
}

fragment DateFieldDefinition on DateFieldGql {
  id
  label
  description
  defaultDate
}

fragment DateTimeFieldDefinition on DateTimeFieldGql {
  id
  label
  description
  defaultDatetime
}

fragment EmailFieldDefinition on EmailFieldGql {
  id
  label
  description
  defaultEmail
}

fragment EnumFieldDefinition on EnumFieldGql {
  id
  label
  description
  allowedValues
  defaultStr
}

fragment FloatFieldDefinition on FloatFieldGql {
  id
  label
  description
  defaultFloat
  geFloat
  leFloat
}

fragment IntFieldDefinition on IntFieldGql {
  id
  label
  description
  defaultInt
  geInt
  leInt
}

fragment JsonFieldDefinition on JsonFieldGql {
  id
  label
  description
  defaultDict
}

fragment ListFieldDefinition on ListFieldGql {
  id
  label
  description
  defaultList
}

fragment StrFieldDefinition on StrFieldGql {
  id
  label
  description
  defaultStr
  minLength
  maxLength
}

fragment UuidFieldDefinition on UuidFieldGql {
  id
  label
  description
  defaultUuid
}

fragment ObjectFieldDefinition on ObjectFieldGql {
  id
  label
  description
}
"""

# -- query record
