from html import escape as html_escape


def escape(text: str) -> str:
    return html_escape(text, quote=False)


def format_richtext(template: str, *args: str) -> str:
    result = template
    for index, value in enumerate(args, start=1):
        result = result.replace(f"%{index}", value)
    return result


def link(url: str, text: str, color: str = "#0984e3") -> str:
    safe_url = html_escape(url, quote=True)
    safe_text = escape(text)
    return (
        f'<a href="{safe_url}">' f'<span style=" text-decoration: underline; color:{color};">{safe_text}</span>' f"</a>"
    )


def bold(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def italic(text: str) -> str:
    return f'<span style=" font-style:italic;">{escape(text)}</span>'


def code(text: str) -> str:
    return f"<span style=\" font-family:'Courier';\">{escape(text)}</span>"
