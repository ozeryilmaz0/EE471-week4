"""Library model: media items, books, DVDs and a collection with CRUD methods."""


class ItemNotFoundError(Exception):
    """Raised when no item in the collection has the requested id."""


class ItemStateError(Exception):
    """Raised when an action does not fit the item's current state."""


def _validate_text(field, value):
    """Return the stripped string, or raise ValueError if it is empty."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_positive_int(field, value):
    """Return the value, or raise ValueError if it is not a positive integer."""
    # bool is a subclass of int in Python, so True would pass as 1 otherwise.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


class MediaItem:
    """A generic item that can be borrowed from a library.

    Attributes:
        id: Unique number given by LibraryCollection.add_item(), or None.
        title: Title of the item.
        author: Author, director or creator of the item.
        is_available: True if the item is on the shelf.
    """

    TYPE = "item"
    VALIDATORS = {"title": _validate_text, "author": _validate_text}
    PROTECTED_FIELDS = ("id", "type", "is_available")

    def __init__(self, title, author, is_available=True):
        """Create an item; it has no id until it is added to a collection."""
        self.id = None
        self.title = _validate_text("title", title)
        self.author = _validate_text("author", author)
        self.is_available = is_available

    @classmethod
    def check_field_names(cls, fields, require_all=False):
        """Raise ValueError for protected, unknown or (optionally) missing fields."""
        protected = sorted(set(fields) & set(cls.PROTECTED_FIELDS))
        if protected:
            raise ValueError(f"Cannot change {', '.join(protected)}")
        unknown = sorted(set(fields) - set(cls.VALIDATORS))
        if unknown:
            raise ValueError(
                f"Unknown field(s) for {cls.TYPE}: {', '.join(unknown)}")
        if require_all:
            missing = [name for name in cls.VALIDATORS if name not in fields]
            if missing:
                raise ValueError(f"Missing field(s): {', '.join(missing)}")

    def update(self, /, **fields):
        """Change some editable fields; nothing changes if any value is invalid."""
        if not fields:
            raise ValueError("No fields to update")
        self.check_field_names(fields)
        # Validate everything first so a bad value cannot leave a half-updated item.
        cleaned = {name: self.VALIDATORS[name](name, value)
                   for name, value in fields.items()}
        for name, value in cleaned.items():
            setattr(self, name, value)

    def replace(self, /, **fields):
        """Set all editable fields at once; every editable field is required."""
        self.check_field_names(fields, require_all=True)
        self.update(**fields)

    def checkout(self):
        """Check the item out.

        Returns:
            "Successful checkout".

        Raises:
            ItemStateError: If the item is already checked out.
        """
        if not self.is_available:
            raise ItemStateError(f'"{self.title}" is already checked out')
        self.is_available = False
        return "Successful checkout"

    def return_item(self):
        """Return the item to the shelf.

        Returns:
            "Successful return".

        Raises:
            ItemStateError: If the item is not checked out.
        """
        if self.is_available:
            raise ItemStateError(f'"{self.title}" is not checked out')
        self.is_available = True
        return "Successful return"

    def to_dict(self):
        """Return the item as a JSON-ready dictionary."""
        return {
            "id": self.id,
            "type": self.TYPE,
            "title": self.title,
            "author": self.author,
            "is_available": self.is_available,
        }

    def __str__(self):
        """Return the item as "Title by Author [Available/Checked Out]"."""
        status = "Available" if self.is_available else "Checked Out"
        return f"{self.title} by {self.author} [{status}]"


class Book(MediaItem):
    """A book that also records how many pages it has."""

    TYPE = "book"
    VALIDATORS = {**MediaItem.VALIDATORS, "page_count": _validate_positive_int}

    def __init__(self, title, author, page_count, is_available=True):
        """Create a book with the given page count."""
        super().__init__(title, author, is_available)
        self.page_count = _validate_positive_int("page_count", page_count)

    def to_dict(self):
        """Return the base dictionary plus page_count."""
        return {**super().to_dict(), "page_count": self.page_count}

    def __str__(self):
        """Return the base description followed by the page count."""
        return f"{super().__str__()} - {self.page_count} pages"


class DVD(MediaItem):
    """A DVD that records its running time and needs careful handling."""

    TYPE = "dvd"
    VALIDATORS = {**MediaItem.VALIDATORS, "duration": _validate_positive_int}

    def __init__(self, title, author, duration, is_available=True):
        """Create a DVD with the given running time in minutes."""
        super().__init__(title, author, is_available)
        self.duration = _validate_positive_int("duration", duration)

    def checkout(self):
        """Check the DVD out and add a care reminder to the success message."""
        # The parent raises ItemStateError on failure, so the reminder is only
        # added when the disc is really handed over.
        message = super().checkout()
        return f"{message}. Handle with care: Do not scratch the disc."

    def to_dict(self):
        """Return the base dictionary plus duration."""
        return {**super().to_dict(), "duration": self.duration}

    def __str__(self):
        """Return the base description followed by the running time."""
        return f"{super().__str__()} - {self.duration} min"


class LibraryCollection:
    """A container that stores media items and gives each one a unique id."""

    ITEM_CLASSES = {"book": Book, "dvd": DVD}
    TYPE_FILTERS = ("item", "book", "dvd")

    def __init__(self):
        """Create an empty collection."""
        self.items = []
        self._next_id = 1

    def add_item(self, item):
        """Add an item, give it the next id and return that id."""
        if not isinstance(item, MediaItem):
            raise ValueError("Only MediaItem objects can be added")
        # A counter instead of len(self.items) so ids are never reused after a delete.
        item.id = self._next_id
        self._next_id += 1
        self.items.append(item)
        return item.id

    def create_item(self, item_type, /, **fields):
        """Build a Book or DVD from plain values, add it and return it."""
        item_class = self.ITEM_CLASSES.get(item_type)
        if item_class is None:
            raise ValueError('type must be "book" or "dvd"')
        item_class.check_field_names(fields, require_all=True)
        item = item_class(**fields)
        self.add_item(item)
        return item

    def get_item(self, item_id):
        """Return the item with this id, or raise ItemNotFoundError."""
        for item in self.items:
            if item.id == item_id:
                return item
        raise ItemNotFoundError(f"Item {item_id} not found")

    def list_items(self, available=None, item_type=None):
        """Return all items, optionally filtered by availability and type."""
        if available not in (None, True, False):
            raise ValueError("available must be True, False or None")
        if item_type is not None and item_type not in self.TYPE_FILTERS:
            raise ValueError(f"type must be one of: {', '.join(self.TYPE_FILTERS)}")
        return [
            item for item in self.items
            if (available is None or item.is_available == available)
            and (item_type is None or item.TYPE == item_type)
        ]

    def list_available(self):
        """Return the titles of all items that are currently available."""
        return [item.title for item in self.list_items(available=True)]

    def update_item(self, item_id, /, **fields):
        """Change some editable fields of an item and return the item."""
        item = self.get_item(item_id)
        item.update(**fields)
        return item

    def replace_item(self, item_id, /, **fields):
        """Replace all editable fields of an item and return the item."""
        item = self.get_item(item_id)
        item.replace(**fields)
        return item

    def remove_item(self, item_id):
        """Remove an item; checked-out items cannot be removed."""
        item = self.get_item(item_id)
        if not item.is_available:
            raise ItemStateError("Cannot delete a checked-out item")
        self.items.remove(item)
