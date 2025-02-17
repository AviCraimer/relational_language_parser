from deepdiff import DeepDiff
from pprint import pprint


def equals(a: dict, b: dict):
    return DeepDiff(a, b) == {}


from lark import Lark, Transformer


grammar = """
    ?start: relation_expr

    ?relation_expr: rel_body (":" dom_cod)?  -> relation_expr_trans

    ?rel_body: rel_composed_level

    ?rel_composed_level: rel_coproduct_level
                    | rel_composed_level ";" rel_coproduct_level  -> rel_composed_trans

    ?rel_coproduct_level: rel_product_level
                        | rel_coproduct_level "+" rel_product_level  -> rel_coproduct_trans

    ?rel_product_level: rel_atomic_level
                    | rel_product_level "*" rel_atomic_level  -> rel_product_trans

    ?rel_atomic_level: rel_atomic
                    | rel_parens

    ?rel_parens: "(" rel_body ")"

    rel_atomic: IDENTIFIER ":" dom_cod   -> rel_atomic_trans

    dom_cod: set_expr "->" set_expr    -> dom_cod_trans

    // Set expressions with precedence
    ?set_expr: set_coproduct

    ?set_coproduct: set_product
           | set_coproduct "+" set_product   -> set_coproduct_trans

    ?set_product: set_atomic
                | set_product "*" set_atomic  -> set_product_trans

    ?set_atomic: IDENTIFIER  -> set_atomic_trans
               | "(" set_expr ")"

    IDENTIFIER: /[a-zA-Z][a-zA-Z0-9_]*/

    %import common.WS
    %ignore WS
"""


class ASTTransformer(Transformer):
    def relation_expr_trans(self, args):
        if len(args) == 1:
            return args[0]
        else:
            rel, outer_dom_cod = args
            if (
                # This compares the domain and codomain which is calculated bottom up from components against the domain codomain explicitly annotating the composite expression.
                not equals(rel["dom_cod"]["domain"], outer_dom_cod["domain"])
                or not equals(rel["dom_cod"]["codomain"], outer_dom_cod["codomain"])
            ):
                raise ValueError(
                    f"Type mismatch: expression has type {rel['dom_cod']['domain']} -> {rel['dom_cod']['codomain']}, "
                    f"but was declared with type {outer_dom_cod['domain']} -> {outer_dom_cod['codomain']}"
                )
            return rel

    def rel_atomic_trans(self, args):
        rel, dom_cod = args

        return {
            "type": "rel_atomic",
            "rel_name": str(rel),
            "dom_cod": dom_cod,
        }

    def rel_composed_trans(self, args):
        left, right = args
        # Checks the required invariant for R;S that the codomain of R equals the domain of S.
        if not equals(left["dom_cod"]["codomain"], right["dom_cod"]["domain"]):
            raise ValueError(
                f"Type mismatch in composition: {left['dom_cod']['codomain']} ≠ {right['dom_cod']['domain']}"
            )
        return {
            "type": "relation_composition",
            "left": left,
            "right": right,
            "dom_cod": {
                "domain": left["dom_cod"]["domain"],
                "codomain": right["dom_cod"]["codomain"],
            },
        }

    def rel_coproduct_trans(self, args):
        left, right = args
        return {
            "type": "rel_coproduct",
            "left": left,
            "right": right,
            "dom_cod": {
                "domain": {
                    "type": "set_coproduct",
                    "left": left["dom_cod"]["domain"],
                    "right": right["dom_cod"]["domain"],
                },
                "codomain": {
                    "type": "set_coproduct",
                    "left": left["dom_cod"]["codomain"],
                    "right": right["dom_cod"]["codomain"],
                },
            },
        }

    def rel_product_trans(self, args):
        left, right = args
        return {
            "type": "rel_product",
            "left": left,
            "right": right,
            "dom_cod": {
                "domain": {
                    "type": "set_product",
                    "left": left["dom_cod"]["domain"],
                    "right": right["dom_cod"]["domain"],
                },
                "codomain": {
                    "type": "set_product",
                    "left": left["dom_cod"]["codomain"],
                    "right": right["dom_cod"]["codomain"],
                },
            },
        }

    def dom_cod_trans(self, args):
        domain, codomain = args
        return {"type": "dom_cod", "domain": domain, "codomain": codomain}

    def set_atomic_trans(self, args):
        return str(args[0])

    def set_coproduct_trans(self, args):
        left, right = args
        return {"type": "set_coproduct", "left": left, "right": right}

    def set_product_trans(self, args):
        left, right = args
        return {"type": "set_product", "left": left, "right": right}


def parse(text):
    parser = Lark(grammar, parser="lalr", transformer=ASTTransformer())
    return parser.parse(text)


# Tests
if __name__ == "__main__":
    # Test 1: Basic atomic relation (must have type)
    test1 = "R : A -> B * C"
    print("Test 1 (atomic relation):")
    pprint(parse(test1))

    # Test 2: Composite relation with inferred type
    test2 = "(R : A -> C + B);(S : C+ B -> C)"
    print("\nTest 2 (composite with inferred type):")
    pprint(parse(test2))

    # Test 3: Composite relation with explicit type (matching)
    test3 = "(R : A -> B);(S : B -> C):A -> C"
    print("\nTest 3 (composite with matching explicit type):")
    pprint(parse(test3))

    # Test 4: Composite relation with wrong explicit type
    test4 = "(R : A -> B);(S : B -> C):A -> D"
    try:
        parse(test4)
    except ValueError as e:
        print("\nTest 4 (type mismatch) failed as expected:", e)

    # Test 5: Composition type mismatch
    test5 = "(R : A -> B);(S : C -> D)"
    try:
        parse(test5)
    except ValueError as e:
        print("\nTest 5 (composition mismatch) failed as expected:", e)

    # Test 6: Complex set expressions
    test6 = "(R : A * B -> C);(S : C -> D + E)"
    print("\nTest 6 (complex set expressions):")
    pprint(parse(test6))

    # Test 7 relation product
    test7 = "(R : A -> B) * (S : C -> D)"
    print("Test 7 (relation product with inferred type):")
    pprint(parse(test7))

    # Test 8 relation product with explicit type
    test8 = "(R : A -> B) * (S : C -> D) : A * C -> B * D"
    print("\nTest 8 (relation product with explicit type):")
    pprint(parse(test8))

    # Test 9 relation product with wrong explicit type
    test9 = "(R : A -> B) * (S : C -> D) : A * C -> B * E"
    try:
        parse(test9)
    except ValueError as e:
        print("\nTest 9 (type mismatch) failed as expected:", e)

    # Test 10a mixed product and composition
    test10a = "((R : A -> B) * (S : C -> D));(T : B * D -> E)"
    parse10a = parse(test10a)
    print("\nTest 10a (product and composition):")
    pprint(parse10a)

    # Test 10b mixed product and composition
    test10b = "(R : A -> B) * (S : C -> D);(T : B * D -> E)"
    parse10b = parse(test10b)
    print("\nTest 10b (product and composition):")
    pprint(parse10b)

    # Test basic relation coproduct
    test11 = "(R : A -> B) + (S : C -> D)"
    print("Test 11 (basic coproduct with inferred type):", parse(test11))

    # Test coproduct with explicit type
    test12 = "(R : A -> B) + (S : C -> D) : A + C -> B + D"
    print("\nTest 12 (coproduct with explicit type):", parse(test12))

    # Test coproduct with wrong explicit type
    test13 = "(R : A -> B) + (S : C -> D) : A + C -> B + E"
    try:
        parse(test13)
    except ValueError as e:
        print("\nTest 13 (type mismatch) failed as expected:", e)

    # Test precedence with product (+ binds looser than *)
    test14 = "(R : A -> B) * (S : C -> D) + (T : E -> F) * (U : G -> H)"
    print("\nTest 14 (coproduct of products):", parse(test14))
    # Should parse as (R*S) + (T*U) with type (A*C + E*G) -> (B*D + F*H)

    # Test precedence with composition (; binds looser than +)
    test15 = "(R : A -> B) + (S : C -> D);(T : B + D -> E)"
    print("\nTest 5 (composition after coproduct):", parse(test15))
    # Should parse as (R+S);T with type A+C -> E

    # Test complex combination
    test16 = "((R : A -> B) * (S : C -> D) + (T : E -> F));(U : B * D + F -> G)"
    print("\nTest 6 (composition of coproduct of products):", parse(test16))
    # Should parse as ((R*S)+(T));U with type (A*C + E) -> G

    # Test multiple coproducts
    test17 = "(R : A -> B) + (S : C -> D) + (T : E -> F)"
    print("\nTest 17 (multiple coproducts):", parse(test17))
    # Should parse as (R+S)+T with type A+C+E -> B+D+F

    # Test parentheses overriding precedence
    test18 = "((R : A -> B) + (S : C -> D)) * (T : E -> F)"
    print("\nTest 18 (parenthesized coproduct then product):", parse(test18))
    # should have type (A + C) * E -> (B + D) * F

    # Test complex type expressions in coproduct
    test19 = "(R : A * B -> C + D) + (S : E * F -> G + H)"
    print("\nTest 19 (coproduct with complex types):", parse(test19))
    # Should have type (A*B + E*F) -> (C+D + G+H)
