import os

def create_post_model_from_backlog(data):
    # TODO: mock
    parsed_data = parse_backlog_model(data)

    return {
        "username": "uchia",
        "content": "新しい更新通知なのです。",
        "embeds": [
            {
                "author": {
                    "name": parsed_data["author_name"],
                },
                "title": parsed_data["title"],
                "url": parsed_data["title_url"],
                "description": parsed_data["description"],
                "fields": [
                    {
                        "name": "種別", 
                        "value": parsed_data["issue_type"] or "未指定",
                        "inline": True,
                    },
                    {
                        "name": "担当者",
                        "value": parsed_data["assignee"] or "未指定",
                        "inline": True,
                    },
                    {
                        "name": "優先度", 
                        "value": parsed_data["priority"] or "未指定",
                        "inline": True,
                    },
                    {
                        "name": "マイルストーン", 
                        "value": parsed_data["milestone"] or "未指定",
                        "inline": True,
                    },
                    {
                        "name": "発生バージョン", 
                        "value": parsed_data["versions"] or "未指定",
                        "inline": True,
                    },
                    {
                        "name": "期限日", 
                        "value": parsed_data["due_date"] or "未指定",
                        "inline": True,
                    },
                ],
            },
        ],
    }

def parse_backlog_model(data):
    # TODO: タイプ別に作る必要があるかも。とりあえず issue 周りだけ対応してみる
    backlog_base_url = os.environ.get("BACKLOG_BASE_URL")

    url_base = "{backlog_base_url}-{issue_id}"
    project = data["project"]
    action_type = data["type"]
    content = data["content"]
    user = data["createdUser"]

    def _parse_some_versions(content_, key):
        m = content_[key]
        if m:
            # 1番目決め打ち
            return m[0]["name"]
        return "指定なし"

    return {
        "author_name": user["name"],
        "title": content["summary"],
        "description": content["description"][:1000],
        "title_url": url_base.format(**{
            "backlog_base_url": backlog_base_url,
            "issue_id": content["id"],
        }),
        "issue_type": content["issueType"]["name"],
        "assignee": content.get("assignee", "未指定"),
        "priority": content["priority"]["name"],
        "milestone": _parse_some_versions(content, "milestone"),
        "versions": _parse_some_versions(content, "versions"),
        "due_date": content.get("dueDate", "未指定"),
    }
