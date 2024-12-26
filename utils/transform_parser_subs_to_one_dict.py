from collections import defaultdict
from typing import Dict, List

from globals.services import ServiceTypes


def transform_parser_subs_to_one_dict(
    consulate_subscribers, vfs_subscribers
) -> Dict[str, Dict[str, List[str]]]:

    transformed = defaultdict(
        lambda: {ServiceTypes.VFS: [], ServiceTypes.CONSULATE: []}
    )

    # Обработка consulate_subscribers
    for city, chat_ids in consulate_subscribers.items():
        for chat_id in chat_ids:
            transformed[chat_id][ServiceTypes.CONSULATE].append(city)

    # Обработка vfs_subscribers
    for city, chat_ids in vfs_subscribers.items():
        for chat_id in chat_ids:
            transformed[chat_id][ServiceTypes.VFS].append(city)

    return transformed
