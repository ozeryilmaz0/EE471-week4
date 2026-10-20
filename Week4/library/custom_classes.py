"""Library media classes for the EE471 Week 3 OOP exercise."""


class MediaItem:
    """A generic item that can be borrowed from a library.

    Attributes:
        title: Title of the item.
        author: Author, director or creator of the item.
        is_available: True if the item is on the shelf, False if it is
            checked out.
    """

    def __init__(self, title, author, is_available=True):
        """Create a media item that is available by default."""
        self.title = title
        self.author = author
        self.is_available = is_available

    def checkout(self):
        """Check the item out if it is available.

        Returns:
            "Successful checkout" if the item was available,
            otherwise "Already out".
        """
        if self.is_available:
            self.is_available = False
            return "Successful checkout"
        return "Already out"

    def return_item(self):
        """Mark the item as returned so it can be borrowed again."""
        self.is_available = True

    def __str__(self):
        """Return the item as "Title by Author [Available/Checked Out]"."""
        status = "Available" if self.is_available else "Checked Out"
        return f"{self.title} by {self.author} [{status}]"


class Book(MediaItem):
    """A book that also records how many pages it has.

    Attributes:
        page_count: Number of pages in the book.
    """

    def __init__(self, title, author, page_count, is_available=True):
        """Create a book with the given page count."""
        super().__init__(title, author, is_available)
        self.page_count = page_count

    def __str__(self):
        """Return the base description followed by the page count."""
        return f"{super().__str__()} - {self.page_count} pages"


class DVD(MediaItem):
    """A DVD that records its running time and needs careful handling.

    Attributes:
        duration: Running time in minutes.
    """

    def __init__(self, title, author, duration, is_available=True):
        """Create a DVD with the given running time in minutes."""
        super().__init__(title, author, is_available)
        self.duration = duration

    def checkout(self):
        """Check the DVD out and remind the borrower to handle it carefully.

        Returns:
            The same message as MediaItem.checkout().
        """
        # Delegate to the parent so future changes to the checkout rules
        # also apply to DVDs.
        result = super().checkout()
        # Remind only when the disc is actually handed over.
        if result == "Successful checkout":
            print("Handle with care: Do not scratch the disc.")
        return result


class LibraryCollection:
    """A container that holds the media items of a library.

    Attributes:
        items: MediaItem objects, including subclasses such as Book and DVD.
    """

    def __init__(self):
        """Create an empty collection."""
        self.items = []

    def add_item(self, item):
        """Add a MediaItem or one of its subclasses to the collection."""
        self.items.append(item)

    def list_available(self):
        """Return the titles of all items that are currently available."""
        return [item.title for item in self.items if item.is_available]