import pytest
from relational_language_parser.parser import parse


def test_atomic_relation():
    """Test basic atomic relation with type annotation"""
    result = parse("R : A -> B * C")

    assert result["type"] == "program"
    assert len(result["expr"]) == 1

    relation = result["expr"][0]["expr"]
    assert relation["type"] == "relation"
    assert relation["operation"] == "atomic"
    assert relation["rel_name"] == "R"

    # Check domain and codomain structure
    dom_cod = relation["dom_cod"]
    assert dom_cod["domain"]["name"] == "A"
    assert dom_cod["codomain"]["operation"] == "product"
    assert dom_cod["codomain"]["left"]["name"] == "B"
    assert dom_cod["codomain"]["right"]["name"] == "C"


def test_composite_relation_inferred_type():
    """Test composite relation with inferred type"""
    result = parse("(R : A -> C + B);(S : C + B -> C)")

    assert result["type"] == "program"
    relation = result["expr"][0]["expr"]
    assert relation["type"] == "relation"
    assert relation["operation"] == "composition"

    # Check left and right parts exist
    assert "left" in relation
    assert "right" in relation

    # Check types match at composition boundary
    assert (
        relation["left"]["dom_cod"]["codomain"]
        == relation["right"]["dom_cod"]["domain"]
    )


def test_composite_relation_explicit_type():
    """Test composite relation with explicit type annotation"""
    result = parse("(R : A -> B);(S : B -> C):A -> C")

    composite = result["expr"][0]["expr"]
    assert composite["operation"] == "composition"

    # Check overall domain and codomain
    assert composite["dom_cod"]["domain"]["name"] == "A"
    assert composite["dom_cod"]["codomain"]["name"] == "C"


def test_composite_relation_type_mismatch():
    """Test that type mismatches are caught"""
    with pytest.raises(ValueError, match="Type mismatch"):
        parse("(R : A -> B);(S : B -> C):A -> D")


def test_composition_type_mismatch():
    """Test that composition type mismatches are caught"""
    with pytest.raises(ValueError, match="Type mismatch in composition"):
        parse("(R : A -> B);(S : C -> D)")


def test_relation_product():
    """Test relation product with inferred type"""
    result = parse("(R : A -> B) * (S : C -> D)")

    relation = result["expr"][0]["expr"]
    assert relation["operation"] == "product"

    # Check domain structure
    dom = relation["dom_cod"]["domain"]
    assert dom["operation"] == "product"
    assert dom["left"]["name"] == "A"
    assert dom["right"]["name"] == "C"

    # Check codomain structure
    cod = relation["dom_cod"]["codomain"]
    assert cod["operation"] == "product"
    assert cod["left"]["name"] == "B"
    assert cod["right"]["name"] == "D"


def test_relation_coproduct():
    """Test relation coproduct"""
    result = parse("(R : A -> B) + (S : C -> D)")

    relation = result["expr"][0]["expr"]
    assert relation["operation"] == "coproduct"

    # Check domain structure
    dom = relation["dom_cod"]["domain"]
    assert dom["operation"] == "coproduct"
    assert dom["left"]["name"] == "A"
    assert dom["right"]["name"] == "C"


def test_relation_definition():
    """Test relation definition and usage"""
    result = parse(
        """
    rel R := RR: A -> B
    R;S: B -> C
    """
    )

    assert len(result["expr"]) == 2

    # Check definition
    definition = result["expr"][0]["expr"]
    assert definition["type"] == "definition"
    assert definition["expr_type"] == "relation"
    assert definition["name"] == "R"

    # Check usage
    usage = result["expr"][1]["expr"]
    assert usage["operation"] == "composition"
    assert usage["left"]["operation"] == "defined"
    assert usage["left"]["name"] == "R"


def test_precedence():
    """Test operator precedence with product and coproduct"""
    result = parse("(R : A -> B) * (S : C -> D) + (T : E -> F) * (U : G -> H)")

    relation = result["expr"][0]["expr"]
    assert relation["operation"] == "coproduct"  # + is outermost

    # Check both sides are products
    assert relation["left"]["operation"] == "product"
    assert relation["right"]["operation"] == "product"


def test_complex_composition():
    """Test complex composition with products and coproducts"""
    result = parse("((R : A -> B) * (S : C -> D));(T : B * D -> E)")

    relation = result["expr"][0]["expr"]
    assert relation["operation"] == "composition"
    assert relation["left"]["operation"] == "product"

    # Verify type compatibility
    left_cod = relation["left"]["dom_cod"]["codomain"]
    right_dom = relation["right"]["dom_cod"]["domain"]
    assert left_cod == right_dom


def test_multiple_statements():
    """Test parsing multiple statements"""
    result = parse(
        """
    set X := A * B
    rel R := S: X -> C
    R: X -> C
    """
    )

    assert len(result["expr"]) == 3
    assert result["expr"][0]["expr"]["type"] == "definition"
    assert result["expr"][0]["expr"]["expr_type"] == "set"
    assert result["expr"][1]["expr"]["type"] == "definition"
    assert result["expr"][1]["expr"]["expr_type"] == "relation"


# Additional helper function for common verifications
def verify_dom_cod(relation, expected_domain, expected_codomain):
    """Helper to verify domain and codomain of a relation"""
    dom_cod = relation["dom_cod"]
    assert dom_cod["domain"]["name"] == expected_domain
    assert dom_cod["codomain"]["name"] == expected_codomain


def test_defined_relation_type_annotation_invariance():
    """Test that explicit type annotation on defined relations is equivalent to using inferred types"""

    # Two equivalent ways to write the same thing
    expr_with_annotation = """
    rel R := RR: A -> B
    R: A -> B;S: B -> C
    """

    expr_without_annotation = """
    rel R := RR: A -> B
    R;S: B -> C
    """

    result_with = parse(expr_with_annotation)
    result_without = parse(expr_without_annotation)

    # The ASTs should be identical
    assert result_with == result_without


def test_relation_composition_spacing_invariance():
    """Test that whitespace and newlines don't affect the AST except for separating statements."""

    expr1 = """R: A -> B;S: B -> C"""
    expr2 = """


    R:A->B;S: B -> C


    """
    expr3 = "R: A -> B; S: B -> C"

    result1 = parse(expr1)
    result2 = parse(expr2)
    result3 = parse(expr3)

    assert result1 == result2
    assert result2 == result3


def test_parentheses_invariance():
    """Test that redundant parentheses produce the same AST"""

    expr1 = "(R: A -> B);S: B -> C"
    expr2 = "R: A -> B;S: B -> C"
    expr3 = "(R: A -> B;(S: B -> C))"

    result1 = parse(expr1)
    result2 = parse(expr2)
    result3 = parse(expr3)

    assert result1 == result2
    assert result2 == result3


def test_product_composition_invariance():
    """Test that product composition is invariant to parentheses placement"""

    expr1 = "((R : A -> B) * (S : C -> D));(T : B * D -> E)"
    expr2 = "(R : A -> B) * (S : C -> D);(T : B * D -> E)"

    result1 = parse(expr1)
    result2 = parse(expr2)

    assert result1 == result2


def test_coproduct_invariance():
    """Test that coproduct is invariant to spacing and parentheses"""

    expr1 = """
    (R: A -> B) + S: B -> C"""
    expr2 = "(R: A -> B) + (S: B -> C))"
    expr3 = "R: A -> B + (S: B -> C)"
    # Note: "R: A -> B + S: B -> C" is not valid syntax because there is ambiguity whether B + S is the codomain of R.

    # Note you need a bracked on one of the relation components or it is ambiguous whether the codomain of R is a set named B + S.

    result1 = parse(expr1)
    result2 = parse(expr2)
    result3 = parse(expr3)
    assert result1 == result2
    assert result2 == result3


def test_definition_spacing_invariance():
    """Test that definitions are invariant to spacing and newlines outside the statment"""

    expr1 = "rel R := RR: A -> B"
    expr2 = """

    rel R :=    RR: A -> B


    """
    expr3 = "rel R:=RR:A->B"

    result1 = parse(expr1)
    result2 = parse(expr2)
    result3 = parse(expr3)

    assert result1 == result2
    assert result2 == result3


def test_complex_expression_invariance():
    """Test invariance in complex expressions with multiple operators"""

    expr1 = "(R: A -> B) * (S: C -> D) + (T: E -> F);(U: (B * D) + F -> G)"
    expr2 = """
    (R: A -> B * S: C -> D) + T: E -> F;U: (B * D + F) -> G
    """

    result1 = parse(expr1)
    result2 = parse(expr2)

    assert result1 == result2


def test_type_annotation_equivalence():
    """Test that equivalent type annotations produce the same AST"""

    expr1 = "(R:A->B;S:B->C): A -> C"
    expr2 = "R:A->B;S:A->C"

    result1 = parse(expr1)
    result2 = parse(expr2)

    assert result1 == result2


def test_multiline_program_invariance():
    """Test that programs with different formatting produce the same AST"""

    program1 = """

    rel R := RR: A -> B
    rel S := SS: B -> C
    R;S: A -> C
    """

    program2 = """rel R := RR: A -> B
            rel S := SS: B -> C
    R;S"""

    program3 = "rel R := RR: A -> B\nrel S := SS: B -> C\nR;S: A -> C"

    result1 = parse(program1)
    result2 = parse(program2)
    result3 = parse(program3)

    assert result1 == result2
    assert result2 == result3
