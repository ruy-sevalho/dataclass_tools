from dataclasses import asdict, dataclass

from hypothesis import given, strategies as st

from dataclass_tools.tools import serialize_dataclass


@given(st.floats(), st.characters())
def test_float_str_flat_strucuture(age, name):
    @dataclass
    class Child:
        age: float
        name: str

    child = Child(age=age, name=name)
    assert serialize_dataclass(child) == asdict(child)


@given(st.tuples(st.tuples(st.floats(), st.characters())), st.characters())
def test_float_str_nested_strucuture(childs_tuples, name_parent):
    @dataclass
    class Child:
        age: float
        name: str

    @dataclass
    class Parent:
        childs: list[Child]
        name: str

    childs = tuple(Child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent = Parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)
