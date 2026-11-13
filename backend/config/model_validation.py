"""Model validation helpers that avoid extra database round trips."""


def full_clean_without_db_lookups(instance) -> None:
    """Run ``full_clean`` without the validation steps that query the database.

    ``Model.full_clean`` normally issues one ``SELECT`` per foreign key (to check the
    row exists) and a ``SAVEPOINT``/``SELECT``/``RELEASE`` triple per constraint. On a
    remote database each of those is a network round trip. This keeps field
    validation, ``clean()`` business rules and non-constraint unique checks, and
    leaves foreign-key and constraint enforcement to the database itself.

    Use only on models written by trusted server-side code, never to validate raw
    client-supplied foreign-key values.
    """
    relation_fields = [f.name for f in instance._meta.concrete_fields if f.is_relation]
    instance.full_clean(exclude=relation_fields, validate_constraints=False)
