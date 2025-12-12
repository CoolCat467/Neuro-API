"""JSON Schema Types - Schemas for enhanced text editor predictions."""

# Programmed by CoolCat467

from __future__ import annotations

# JSON Schema - Schemas for enhanced text editor predictions
# Copyright (C) 2025  CoolCat467
#
#     This program is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this program.  If not, see
#     <https://www.gnu.org/licenses/>.

__title__ = "json_schema"
__author__ = "CoolCat467"
__license__ = "GNU Lesser General Public License Version 3"


from typing import Final, Literal, TypeAlias, TypedDict

_SimpleTypes: TypeAlias = Literal[
    "array",
    "boolean",
    "integer",
    "null",
    "number",
    "object",
    "string",
]
_SIMPLETYPES_ARRAY: Literal["array"] = "array"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_BOOLEAN: Literal["boolean"] = "boolean"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_INTEGER: Literal["integer"] = "integer"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_NULL: Literal["null"] = "null"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_NUMBER: Literal["number"] = "number"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_OBJECT: Literal["object"] = "object"
"""The values for the '_SimpleTypes' enum"""
_SIMPLETYPES_STRING: Literal["string"] = "string"
"""The values for the '_SimpleTypes' enum"""

_StringArray: TypeAlias = list[str]
"""
uniqueItems: True
default:
  []
"""


_NON_NEGATIVE_INTEGER_DEFAULT0_DEFAULT: Final = 0
"""Default value of the field path 'non negative integer default0'"""


_NonNegativeInteger: TypeAlias = int
"""minimum: 0"""


_NonNegativeIntegerDefault0: TypeAlias = int
"""
minimum: 0
default: 0
"""


CORE_SCHEMA_META_SCHEMA_DEFAULT: TypeAlias = Literal[True]
"""Default value of the field path 'Root'"""


# | default: True
class SchemaObject(TypedDict, total=False):
    """Schema object typed dict."""

    ### | format: uri-reference
    ##$id: str
    ### | format: uri
    ##$schema: str
    ### | format: uri-reference
    ##$ref: str
    ##$comment: str
    title: str
    description: str
    default: object
    # | default: False
    readOnly: bool
    # | default: False
    writeOnly: bool
    examples: list[object]
    # | exclusiveMinimum: 0
    multipleOf: int | float
    maximum: int | float
    exclusiveMaximum: int | float
    minimum: int | float
    exclusiveMinimum: int | float
    # | minimum: 0
    maxLength: _NonNegativeInteger
    # | minimum: 0
    # | default: 0
    minLength: _NonNegativeIntegerDefault0
    # | format: regex
    pattern: str
    # | Core schema meta-schema.
    # |
    # | default: True
    additionalItems: CoreSchemaMetaSchema
    # | default: True
    # |
    # | Aggregation type: anyOf
    items: _CoreSchemaMetaSchemaObjectItems
    # | minimum: 0
    maxItems: _NonNegativeInteger
    # | minimum: 0
    # | default: 0
    minItems: _NonNegativeIntegerDefault0
    # | default: False
    uniqueItems: bool
    # | Core schema meta-schema.
    # |
    # | default: True
    contains: CoreSchemaMetaSchema
    # | minimum: 0
    maxProperties: _NonNegativeInteger
    # | minimum: 0
    # | default: 0
    minProperties: _NonNegativeIntegerDefault0
    # | uniqueItems: True
    # | default:
    # |   []
    required: _StringArray
    # | Core schema meta-schema.
    # |
    # | default: True
    additionalProperties: CoreSchemaMetaSchema
    # | default:
    # |   {}
    definitions: dict[str, CoreSchemaMetaSchema]
    # | default:
    # |   {}
    properties: dict[str, CoreSchemaMetaSchema]
    # | propertyNames:
    # |   format: regex
    # | default:
    # |   {}
    patternProperties: dict[str, CoreSchemaMetaSchema]
    dependencies: dict[
        str,
        _CoreSchemaMetaSchemaObjectDependenciesAdditionalproperties,
    ]
    # | Core schema meta-schema.
    # |
    # | default: True
    propertyNames: CoreSchemaMetaSchema
    const: object
    # | minItems: 1
    # | uniqueItems: True
    enum: list[object]
    # | Aggregation type: anyOf
    type: _CoreSchemaMetaSchemaObjectType
    format: str
    contentMediaType: str
    contentEncoding: str
    # | Core schema meta-schema.
    # |
    # | default: True
    ##if: CoreSchemaMetaSchema
    ### | Core schema meta-schema.
    ### |
    ### | default: True
    then: CoreSchemaMetaSchema
    # | Core schema meta-schema.
    # |
    # | default: True
    ##else: CoreSchemaMetaSchema
    ### | minItems: 1
    allOf: _SchemaArray
    # | minItems: 1
    anyOf: _SchemaArray
    # | minItems: 1
    oneOf: _SchemaArray
    ### | Core schema meta-schema.
    ### |
    ### | default: True
    ##not: CoreSchemaMetaSchema


CoreSchemaMetaSchema: TypeAlias = SchemaObject | Literal[False]
"""
Core schema meta-schema.

default: True
"""

_SchemaArray: TypeAlias = list[CoreSchemaMetaSchema]
"""minItems: 1"""

_CoreSchemaMetaSchemaObjectDependenciesAdditionalproperties: TypeAlias = (
    CoreSchemaMetaSchema | _StringArray
)
"""Aggregation type: anyOf"""


_CoreSchemaMetaSchemaObjectItems: TypeAlias = (
    CoreSchemaMetaSchema | _SchemaArray
)
"""
default: True

Aggregation type: anyOf
"""


_CoreSchemaMetaSchemaObjectTypeAnyof1: TypeAlias = list[_SimpleTypes]
"""
minItems: 1
uniqueItems: True
"""


_CoreSchemaMetaSchemaObjectType: TypeAlias = (
    _SimpleTypes | _CoreSchemaMetaSchemaObjectTypeAnyof1
)
"""Aggregation type: anyOf"""
