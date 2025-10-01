from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def highlight_search(text, search_term):
    """Highlight search term in text with HTML mark tags"""
    if not search_term or not text:
        return text

    # Escape HTML in both text and search term for safety
    from django.utils.html import escape
    text = escape(str(text))
    search_term = escape(str(search_term))

    # Create regex pattern for case-insensitive matching
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)

    # Replace matches with highlighted version
    highlighted = pattern.sub(
        lambda m: f'<mark class="bg-primary/20 text-primary font-medium">{m.group()}</mark>',
        text
    )

    return mark_safe(highlighted)
