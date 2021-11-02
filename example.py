from dataclasses import dataclass, field
from serializer import *


@dataclass
class Child:
    x: float
    y: float
    name: str = field(
        metadata={
            METADATA_KEY: SerializerOptions(subs_by_attr="name"),
        }
    )


@dataclass
class Parent:
    childs: list[Child] = field(
        metadata={
            METADATA_KEY: SerializerOptions(subs_by_attr="name"),
        }
    )
    name: str


@dataclass
class GrandParent:
    child: Parent = field(
        metadata={METADATA_KEY: SerializerOptions(overwrite_key="parent")}
    )
    name: str
    dictionary: dict = field(default_factory=dict)
    b: bool = False


child1 = Child(1.0, 2.0, "leon")
child2 = Child(4, 2, "nathan")
parent = Parent([child1, child2], "dad")
g_parent = GrandParent(
    parent, "grand", {"key": "value", "inner_dict": {"inner_key": "inner_value"}}
)

v = serialize_dataclass(parent)
print(v)
