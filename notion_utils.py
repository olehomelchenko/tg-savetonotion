import requests
import logging
import yaml

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def create_page(token, db_id, message):
    create_page_url = "https://api.notion.com/v1/pages/"
    name = ""
    if message.forward_from:
        name = message.forward_from.first_name
        last_name = message.forward_from.last_name
        username = message.forward_from.username
        username = f" ({username})" if username else ""
        name = f"Forwarded from {name} {last_name}" + username

    if message.forward_from_chat:
        chat_title = message.forward_from_chat.title
        chat_username = message.forward_from_chat.username

        name = f"Forwarded from {chat_title} ({chat_username})"

        forwarded_from_messageid = message.forward_from_message_id
        forwarded_from_channelid = message.forward_from_chat.username
        url = f"https://t.me/{forwarded_from_channelid}/{forwarded_from_messageid}"
    else:
        url = None

    message_dict = message.to_dict()
    if message_dict.get("text"):
        message_dict.pop("text")
    text = message.text_markdown_urled

    content = yaml.dump(message_dict, allow_unicode=True)

    create_page_data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"type": "text", "text": {"content": name}}]},
            "Tags": {
                "multi_select": [
                    {"name": "Telegram"},
                ]
            },
            "url": {"url": url or "https://example.com"},
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
