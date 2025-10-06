from django import template
import re

register = template.Library()


@register.filter
def addbrcommas(value):
    """Replace every comma with a comma + <br> for better visual separation."""
    if not value:
        return ''
    # Avoid double <br> if already present
    return re.sub(r',\s*', ',<br>', str(value))
