import requests
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def create_page(token, db_id, url, text, content=None):
    create_page_url = "https://api.notion.com/v1/pages/"

    create_page_data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"type": "text", "text": {"content": url or ""}}]},
            "Tags": {
                "multi_select": [
                    {"name": "Telegram"},
                ]
            },
            "url": {"url": url or ""},
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text or "",
                            },
                        }
                    ]
                },
            },
            {
                "type": "code",
                "code": {
                    "text": [{"type": "text", "text": {"content": content or ""}}],
                    "language": "yaml",
                },
            },
        ],
    }

    response = requests.post(
        create_page_url,
        json=create_page_data,
        headers={
            "Authorization": token,
            "Notion-Version": "2021-08-16",
        },
    )

    logger.info(response.text)
