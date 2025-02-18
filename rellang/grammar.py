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

    ?rel_parens: "(" rel_expr ")"

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
