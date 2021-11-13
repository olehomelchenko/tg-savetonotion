import requests
import logging
import yaml
import re

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def create_page(token, db_id, message):
    create_page_url = "https://api.notion.com/v1/pages/"
    name = "From "

    url = None
    if message.location:
        name = "Location"

    if message.forward_sender_name:
        name = name + message.forward_sender_name
    if message.forward_from:
        name = message.forward_from.first_name
        last_name = message.forward_from.last_name
        username = message.forward_from.username
        username = f" ({username})" if username else ""
        name = name + f"{name} {last_name}" + username

    if message.forward_from_chat:
        chat_title = message.forward_from_chat.title
        chat_username = message.forward_from_chat.username

        name = name + f"from {chat_title} ({chat_username})"

        forwarded_from_messageid = message.forward_from_message_id
        forwarded_from_channelid = message.forward_from_chat.username

        # if forwarded from channel and the message can have URL, generate the URL and fill the field later
        url = f"https://t.me/{forwarded_from_channelid}/{forwarded_from_messageid}"

    # Generate a dictionary with message metadata and later send it to Notion
    message_dict = message.to_dict()

    # if the message has text, remove it from the metadata object
    if message_dict.get("text"):
        message_dict.pop("text")
    if message_dict.get("caption"):
        message_dict.pop("caption")
    text = message.text_markdown_urled or message.caption_markdown_urled

    create_page_data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"type": "text", "text": {"content": name}}]},
            "Tags": {
                "multi_select": [
                    {"name": "Telegram"},
                ]
            },
        },
        "children": [],
    }

    """
    Look for markdown links in the text. The regexp should match every
    link like this: "[some text](https://some-link.com)", and return a list of two elements for
    each link.
    """

    links = re.findall(r"\[(.*)\]\((.*)\)", text)

    if len(links) > 0:
        # If text has markdown links, add the text regarding that

        create_page_data["children"].append(
            {
                "type": "heading_3",
                "heading_3": {
                    "text": [
                        {"type": "text", "text": {"content": "Links in the article:"}}
                    ]
                },
            }
        )

        # for each link, add it as separate paragraph
        for lnk in links:
            md_text = lnk[0].strip().replace("\u200b", "") or lnk[1]
            md_url = lnk[1]

            create_page_data["children"].append(
                {
                    "type": "paragraph",
                    "paragraph": {
                        "text": [
                            {
                                "type": "text",
                                "plain_text": md_text,
                                "href": md_url,
                                "text": {
                                    "content": md_text,
                                    "link": {"url": md_url},
                                },
                            }
                        ]
                    },
                }
            )

        create_page_data["children"].append({"type": "divider", "divider": {}})
    """
    If the text is too big, you won't be able to send it in one piece to Notion.
    So this part of the script splits large texts by paragraph and sends as separate blocks
    """
    text_list = text.split("\n\n") if text else []
    for chunk in text_list:
        create_page_data["children"].append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk,
                            },
                        }
                    ]
                },
            }
        )

    create_page_data["children"].append({"type": "divider", "divider": {}})

    # Send metadata regarding the post as formatted yaml code

    content = yaml.dump(message_dict, allow_unicode=True)
    create_page_data["children"].append(
        {
            "type": "code",
            "code": {
                "text": [{"type": "text", "text": {"content": content or ""}}],
                "language": "yaml",
            },
        },
    )

    if url:
        create_page_data["properties"]["URL"] = {"url": url}
    elif len(links) > 0:
        create_page_data["properties"]["URL"] = {"url": links[0][1]}

    response = requests.post(
        create_page_url,
        json=create_page_data,
        headers={
            "Authorization": token,
            "Notion-Version": "2021-08-16",
        },
    )

    if response.status_code != 200:
        raise Exception(f"Error: {response.text}")

    logger.info(response)
