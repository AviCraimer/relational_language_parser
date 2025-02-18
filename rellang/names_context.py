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
