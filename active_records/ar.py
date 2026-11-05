import db


class ValidationError(Exception):
    """Business rule violation; the message is shown to the user."""


class ActiveRecord:
    """Base active record. Subclasses define `table` and `columns` ({attribute: column}, without Id)."""

    table = ""
    columns = {}
    defaults = {}
    order_by = "rowid"

    def __init__(self, **values):
        self.id = values.pop("id", None)
        self._persisted = False
        for attr in self.columns:
            setattr(self, attr, values.pop(attr, self.defaults.get(attr)))
        if values:
            raise TypeError(f"Unknown fields for {type(self).__name__}: {', '.join(values)}")

    # --- loading ---

    @classmethod
    def _from_row(cls, row):
        obj = cls.__new__(cls)
        obj.id = row["Id"]
        for attr, col in cls.columns.items():
            setattr(obj, attr, row[col])
        obj._persisted = True
        return obj

    @classmethod
    def _select_sql(cls):
        cols = ", ".join(f'"{c}"' for c in ["Id", *cls.columns.values()])
        return f'SELECT {cols} FROM "{cls.table}"'

    @classmethod
    def get(cls, record_id):
        if record_id is None:
            return None
        row = db.execute(cls._select_sql() + ' WHERE "Id" = ?', (record_id,)).fetchone()
        return cls._from_row(row) if row else None

    @classmethod
    def find(cls, where="", params=(), order_by=None):
        sql = cls._select_sql()
        if where:
            sql += " WHERE " + where
        sql += " ORDER BY " + (order_by or cls.order_by)
        return [cls._from_row(r) for r in db.execute(sql, params)]

    @classmethod
    def all(cls):
        return cls.find()

    # --- persistence ---

    def validate(self):
        pass

    def before_delete(self):
        pass

    def save(self):
        self.validate()
        cols = list(self.columns.values())
        values = [getattr(self, attr) for attr in self.columns]
        with db.transaction() as conn:
            if self._persisted:
                sets = ", ".join(f'"{c}" = ?' for c in cols)
                conn.execute(f'UPDATE "{self.table}" SET {sets} WHERE "Id" = ?', (*values, self.id))
            else:
                if self.id is None:
                    self.id = db.new_id()
                names = ", ".join(f'"{c}"' for c in ["Id", *cols])
                marks = ", ".join("?" * (len(cols) + 1))
                conn.execute(f'INSERT INTO "{self.table}" ({names}) VALUES ({marks})', (self.id, *values))
        self._persisted = True
        return self

    def delete(self):
        self.before_delete()
        with db.transaction() as conn:
            conn.execute(f'DELETE FROM "{self.table}" WHERE "Id" = ?', (self.id,))
        self._persisted = False


def clean_text(value):
    """Strip strings; empty becomes None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None
