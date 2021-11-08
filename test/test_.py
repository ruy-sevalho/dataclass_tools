from dataclasses import asdict, dataclass
from pytest import fixture
from hypothesis import given, strategies as st

from dataclass_tools.tools import serialize_dataclass


@fixture
def child():
    @dataclass
    class Child:
        age: float
        name: str

    return Child


@fixture
def parent(child):
    @dataclass
    class Parent:
        childs: list[child]
        name: str


@given(st.floats(), st.characters())
def test_float_str_flat_strucuture(age, name, child):
    child_instance = child(age=age, name=name)
    assert serialize_dataclass(child_instance) == asdict(child_instance)


@given(
    st.tuples(st.tuples(st.floats(), st.characters())), st.characters(), child, parent
)
def test_float_str_nested_strucuture(childs_tuples, name_parent):

    childs = tuple(child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent_instance = parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)
