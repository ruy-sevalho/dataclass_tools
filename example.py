from dataclasses import dataclass, field, Field
from serializer import *
from enum import Enum, auto


class E(str, Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()


@dataclass
class Child:
    x: float
    y: float
    name: str


@dataclass
class Parent:
    childs: list[Child] = field(
        metadata={METADATA_KEY: SerializerOptions(flatten=True, attr="name")}
    )
    name: str


@dataclass
class GrandParent:
    child: Parent = field(
        metadata={METADATA_KEY: SerializerOptions(overwrite_key="parent")}
    )
    name: str
    dictionary: dict = field(default_factory=dict)


child1 = Child(1, 2, "alan")

child2 = Child(4, 2, "nathan")
parent = Parent([child1, child2], "dad")
g_parent = GrandParent(
    parent, "grand", {"key": "value", "inner_dict": {"inner_key": "inner_value"}}
)

print(f"is instance: {isinstance(parent, DataClass)}")
print(f"{to_dict(g_parent)}")
