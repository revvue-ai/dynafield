# -- Mutate a record schema
"""
mutation M_RecordSchema($schemaToAdd: JSON!) {
  recordSchema(schemaToAdd: $schemaToAdd) {
    count
    schemas {
      id
      name
      description
      fieldDefinitions {
        ... on BoolFieldGql {
          id
          label
          description
          required
          defaultBool
        }
        ... on DateFieldGql {
          id
          label
          description
          required
          defaultDate
        }
        ... on DateTimeFieldGql {
          id
          label
          description
          required
          defaultDatetime
        }
        ... on EmailFieldGql {
          id
          label
          description
          required
          defaultEmail
        }
        ... on EnumFieldGql {
          id
          label
          description
          required
          allowedValues
          defaultStr
        }
        ... on FloatFieldGql {
          id
          label
          description
          required
          geFloat
          leFloat
          defaultFloat
        }
        ... on IntFieldGql {
          id
          label
          description
          required
          geInt
          leInt
          defaultInt
        }
        ... on JsonFieldGql {
          id
          label
          description
          required
          defaultDict
        }
        ... on ListFieldGql {
          id
          label
          description
          required
          defaultList
        }
        ... on StrFieldGql {
          id
          label
          description
          required
          defaultStr
          constraintsStr {
            maxLength
            minLength
          }
        }
        ... on UuidFieldGql {
          id
          label
          description
          required
          defaultUuid
        }
        ... on ObjectFieldGql {
          id
          label
          description
          required
          fields
        }
      }
    }
  }
}
"""

# ---- values
"""
{"schemaToAdd": {
  "id": "0199c0c1-816d-7233-988e-cb355508bef1",
  "name": "customerField",
  "fieldDefinitions": [
    {
      "label": "tag",
      "description": "Constant literal indicating this is a booking super tag.",
      "default_str": "booking",
      "__typename": "StrField"
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
      "__typename": "StrField"
    },
    {
      "label": "lastName",
      "__typename": "StrField"
    },
    {
      "label": "email",
      "__typename": "EmailField"
    },
    {
      "label": "phone",
      "__typename": "StrField"
    },
    {
      "label": "specialRequest",
      "__typename": "StrField"
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
      "__typename": "StrField"
    },
    {
      "label": "evidence",
      "description": "Items explaining why each field was set; text must be a 1:1 copy from the analyzed content.",
      "default_list": [],
      "__typename": "ListField"
    }
    ]
}}
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
