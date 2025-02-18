from deepdiff import DeepDiff
from pprint import pprint


def equals(a: dict, b: dict):
    return DeepDiff(a, b) == {}


from lark import Lark, Transformer

# statements: statement (NEWLINE* statement)*

# ?statement: statement_type NEWLINE
#   | statement_type $END

# ?statement_type:  rel_expr
# | set_definition
# | rel_definition
grammar = """
    ?start: statements
    statements: NEWLINE* terminated_statement* last_statement? -> statements_trans

    ?terminated_statement: statement NEWLINE+ -> default_trans

    ?last_statement: statement -> default_trans

    ?statement: rel_expr
            | set_definition
            | rel_definition

    set_definition: "set" IDENTIFIER ":=" set_expr  -> set_def_trans
    rel_definition:  "rel" IDENTIFIER ":=" rel_expr -> rel_def_trans

    ?rel_expr: rel_body (":" dom_cod)?  -> rel_expr_trans

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
            | IDENTIFIER -> rel_defined_trans




    dom_cod: set_expr "->" set_expr    -> dom_cod_trans

    // Set expressions with precedence
    ?set_expr: set_coproduct -> set_expr_trans

    ?set_coproduct: set_product
           | set_coproduct "+" set_product   -> set_coproduct_trans

    ?set_product: set_atomic
                | set_product "*" set_atomic  -> set_product_trans

    ?set_atomic: set_name
               | "(" set_expr ")"

    ?set_name: IDENTIFIER  -> set_atomic_trans

    IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/

    NEWLINE: /(\\r?\\n|\\r)/

    WS: /[ \t]+/
    %ignore WS

"""


class NamesContext:
    def __init__(self):
        self.set_definitions = {}  # def_name -> set_expr
        self.rel_definitions = {}  # def_name -> rel_expr
        self.used_names = set(["set", "rel"])  # all names (both defined and primitive)

    def define_set(self, name: str, expr: dict):
        if name in self.used_names:
            raise ValueError(f"Name {name} already defined")
        self.set_definitions[name] = expr
        self.use_name(name)

    def define_rel(self, name: str, expr: dict):
        if name in self.used_names:
            raise ValueError(f"Name {name} already defined")
        self.rel_definitions[name] = expr
        self.use_name(name)

    def use_name(self, name: str):
        self.used_names.add(name)
        # Note: We don't check if the name is defined here
        # because it might be a primitive name

    def get_set(self, name: str) -> dict:
        return self.set_definitions[name]

    def get_rel(self, name: str) -> dict:
        return self.rel_definitions[name]


class ASTTransformer(Transformer):

    def __init__(self, names_context: NamesContext):
        super().__init__()
        self.names = names_context  # Pass in the context

    def statements_trans(self, args):
        return {
            "type": "program",
            "expr": [
                {"type": "statement", "expr": arg} for arg in args if str(arg) != "\n"
            ],
        }

    def default_trans(self, args):
        return args[0]

    def set_def_trans(self, args):
        name, expr = args
        name = str(name)
        self.names.define_set(name, expr)
        return {
            "type": "definition",
            "expr_type": "set",
            "name": name,
            "def_body": expr,
        }

    def rel_def_trans(self, args):
        name, expr = args
        name = str(name)
        self.names.define_rel(name, expr)
        return {
            "type": "definition",
            "expr_type": "relation",
            "name": name,
            "def_body": expr,
        }

    def rel_expr_trans(self, args):
        if len(args) == 1:
            # Just return the relation when there's no explicit dom_cod
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
            # Strip the outer level which is not necessary in the AST
            return rel

    def rel_atomic_trans(self, args):
        rel, dom_cod = args
        name = str(rel)
        if name in self.names.rel_definitions:
            expr = self.names.get_rel(name)

            if not equals(dom_cod, expr["dom_cod"]):
                raise ValueError(
                    "Defined Relation has an explicit type annotation which does not match the definition."
                )
            return self.rel_defined_trans(name)
        self.names.use_name(name)
        return {
            "type": "relation",
            "operation": "atomic",
            "rel_name": name,
            "dom_cod": dom_cod,
        }

    def rel_defined_trans(self, args):
        name = str(args[0])
        if name not in self.names.rel_definitions:
            raise ValueError(f"Undefined relation: {name}")
        expr = self.names.get_rel(name)

        # In the AST we store the dom_cod for type checking, but we don't store the definition since we can look it up as needed from the context.
        return {
            "type": "relation",
            "operation": "defined",
            "name": name,
            "dom_cod": expr["dom_cod"],
        }

    def rel_composed_trans(self, args):
        left, right = args
        # Checks the required invariant for R;S that the codomain of R equals the domain of S.
        if not equals(left["dom_cod"]["codomain"], right["dom_cod"]["domain"]):
            raise ValueError(
                f"Type mismatch in composition: {left['dom_cod']['codomain']} ≠ {right['dom_cod']['domain']}"
            )
        return {
            "type": "relation",
            "operation": "composition",
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
            "type": "relation",
            "operation": "coproduct",
            "left": left,
            "right": right,
            "dom_cod": {
                "domain": {
                    "type": "set",
                    "operation": "coproduct",
                    "left": left["dom_cod"]["domain"],
                    "right": right["dom_cod"]["domain"],
                },
                "codomain": {
                    "type": "set",
                    "operation": "coproduct",
                    "left": left["dom_cod"]["codomain"],
                    "right": right["dom_cod"]["codomain"],
                },
            },
        }

    def rel_product_trans(self, args):
        left, right = args
        return {
            "type": "relation",
            "operation": "product",
            "left": left,
            "right": right,
            "dom_cod": {
                "domain": {
                    "type": "set",
                    "operation": "product",
                    "left": left["dom_cod"]["domain"],
                    "right": right["dom_cod"]["domain"],
                },
                "codomain": {
                    "type": "set",
                    "operation": "product",
                    "left": left["dom_cod"]["codomain"],
                    "right": right["dom_cod"]["codomain"],
                },
            },
        }

    def dom_cod_trans(self, args):
        domain, codomain = args
        return {"type": "dom_cod", "domain": domain, "codomain": codomain}

    def set_expr_trans(self, args):
        return args[0]

    def set_atomic_trans(self, args):
        name = str(args[0])
        if name in self.names.set_definitions:
            return {
                "type": "set",
                "operation": "defined",
                "def_name": name,
            }
        else:
            # In futuer I might want to prevent primitive set names from overlappign with primitive relation names. But for now I won't rule it out.
            self.names.use_name(name)
            return {"type": "set", "operation": "atomic", "name": str(args[0])}

    def set_coproduct_trans(self, args):
        left, right = args
        return {"type": "set", "operation": "coproduct", "left": left, "right": right}

    def set_product_trans(self, args):
        left, right = args
        return {"type": "set", "operation": "product", "left": left, "right": right}


def parse(text):
    parser = Lark(grammar, parser="lalr", transformer=ASTTransformer(NamesContext()))
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

    test20a = """

    rel R := RR: A -> B

    R: A -> B;S: B -> C
    """
    test20b = """

    rel R := RR: A -> B

    R;S: B -> C
    """
    print("test 20, defined relation")
    parse20a = parse(test20a)
    parse20b = parse(test20b)
    print("Defined with explicit type", parse20a)
    print("Defined no type", parse20b)
    print("Match: ", equals(parse20a, parse20b))

    test21 = (
        test_definitions
    ) = """
rel R := S : A -> B
rel R2 := R
rel R3 := R2
set A := B * C
set D := A
"""


# def rel_def_def_trans(self, args):
#     # Allows defining a relation with another definition.
#     name, maybe_name = args
#     expr = self.names.get_rel(maybe_name)
#     if not expr:
#         raise ValueError(
#             f"No defined expression or domain codomain for {name} in relation definition body."
#         )
#     self.rel_def_trans([name, expr])
