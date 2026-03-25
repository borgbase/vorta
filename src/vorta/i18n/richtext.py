import logging
import re
from html import escape as html_escape

logger = logging.getLogger(__name__)


def escape(text: str) -> str:
    return html_escape(text, quote=False)


def format_richtext(template: str, *args: str) -> str:
    result = template
    for index in range(len(args), 0, -1):
        result = result.replace(f"%{index}", args[index - 1])
    remaining = re.findall(r'%\d+', result)
    if remaining:
        logger.debug(
            'Unreplaced placeholders in richtext template: %s (template=%r, args=%r)', remaining, template, args
        )
    return result


def link(url: str, text: str, color: str = "#0984e3") -> str:
    safe_url = html_escape(url, quote=True)
    safe_text = escape(text)
    return f'<a href="{safe_url}"><span style=" text-decoration: underline; color:{color};">{safe_text}</span></a>'


def bold(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def italic(text: str) -> str:
    return f'<span style=" font-style:italic;">{escape(text)}</span>'


def code(text: str) -> str:
    return f"<span style=\" font-family:'Courier';\">{escape(text)}</span>"
