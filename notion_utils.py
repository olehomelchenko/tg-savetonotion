import requests
import logging
import yaml
import re

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def add_links_blocks(links, children_block):

    if len(links) > 0:
        # If text has markdown links, add the text regarding that

        children_block.append(
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

            children_block.append(
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

        children_block.append({"type": "divider", "divider": {}})


def add_splitted_text(text, children_block):

    text_list = text.split("\n\n") if text else []
    for chunk in text_list:
        children_block.append(
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

    children_block.append({"type": "divider", "divider": {}})


def add_entities(entities, children_block):
    if len(entities) > 0:
        children_block.append(
            {
                "type": "heading_3",
                "heading_3": {
                    "text": [
                        {
                            "type": "text",
                            "text": {"content": "Entities in the article:"},
                        }
                    ]
                },
            }
        )

    for e in entities:
        children_block.append({"type": "bookmark", "bookmark": {"url": e.url}})


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
    text_markdown = message.text_markdown_urled or message.caption_markdown_urled
    text = message.text or message.caption

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
    link like this: "[some text](https://some-link.com)", and process a list of two elements for
    each link.
    """
    links = re.findall(r"\[(.*)\]\((.*)\)", text_markdown)
    add_links_blocks(links, create_page_data["children"])

    """
    If the text is too big, you won't be able to send it in one piece to Notion.
    So this part of the script splits large texts by paragraph and sends as separate blocks
    """
    add_splitted_text(text, create_page_data["children"])

    # parse entities and save them as bookmarks
    entities = message.entities or message.caption_entities
    entities = list(filter(lambda x: x.url is not None, entities))
    add_entities(entities, create_page_data["children"])

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

    # if post has self link, send it as url. else, look for the first link in the text
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
