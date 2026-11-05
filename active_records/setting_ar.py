import db


class SettingActiveRecord:
    """Key/value app setting. Keyed by `Key` instead of a GUID, so it doesn't extend ActiveRecord."""

    CAMERA_INDEX = "CameraIndex"

    def __init__(self, key, value=None):
        self.key = key
        self.value = value

    @classmethod
    def get(cls, key):
        row = db.execute('SELECT "Key", "Value" FROM Setting WHERE "Key" = ?', (key,)).fetchone()
        return cls(row["Key"], row["Value"]) if row else None

    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.get(key)
        return setting.value if setting and setting.value is not None else default

    @classmethod
    def set_value(cls, key, value):
        cls(key, value).save()

    def save(self):
        with db.transaction() as conn:
            conn.execute(
                'INSERT INTO Setting ("Key", "Value") VALUES (?, ?) '
                'ON CONFLICT("Key") DO UPDATE SET "Value" = excluded."Value"',
                (self.key, None if self.value is None else str(self.value)),
            )
        return self

    def delete(self):
        with db.transaction() as conn:
            conn.execute('DELETE FROM Setting WHERE "Key" = ?', (self.key,))
