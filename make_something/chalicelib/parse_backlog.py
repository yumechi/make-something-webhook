from typing import Dict, Any
import os
from abc import ABC, abstractmethod


def create_post_body(data):
    action_type = data["type"]
    mp = {
        1: CreateIssueModel,
    }
    cl = mp.get(action_type)
    if not cl:
        msg = f"Unknown type: {action_type}"
        print(msg)
        raise ValueError(msg)
    return cl(data).parse()


class ParseMixin(ABC):
    def __init__(self, data):
        self.data = data

    def parse(self) -> Dict[str, Any]:
        base = {
            "username": "uchia",
            "content": "新しい更新通知なのです。",
        }
        base.update(self.parse_base_infomation())
        fields = self._parse()
        if fields:
            base["embeds"][0]["fields"] = fields
        return base

    @abstractmethod
    def _parse(self) -> Dict[str, Any]:
        return {}

    @abstractmethod
    def get_title_url(self):
        pass

    @abstractmethod
    def get_title(self):
        pass

    @abstractmethod
    def get_username(self):
        pass

    @abstractmethod
    def get_description(self):
        pass

    def parse_base_infomation(self):
        return {
            "embeds": [
                {
                    "author": {
                        "name": self.get_username(),
                    },
                    "title": self.get_title(),
                    "url": self.get_title_url(),
                    "description": self.get_description(),
                }
            ],
        }


class IssueBase(object):
    def __init__(self, data):
        self.data = data

    def get_title_url(self):
        base_url = os.environ.get("BACKLOG_BASE_URL")
        project_prefix = os.environ.get("PROJECT_PREFIX")
        issue_id = self.data["content"]["id"]
        return f"{base_url}/view/{project_prefix}-{issue_id}"

    def get_title(self):
        return self.data["content"].get("summary", "タイトルなし")

    def get_username(self):
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self):
        return self.data["content"].get("description", "説明なし")


class CreateIssueModel(IssueBase, ParseMixin):
    def _parse(self):
        fields = self.create_fields(self.data)

        return [e for e in [
            {
                "name": "種別",
                "value": fields.get("issue_type", "未指定"),
                "inline": True,
            },
            {
                "name": "担当者",
                "value": fields.get("assignee", "未指定"),
                "inline": True,
            },
            {
                "name": "優先度",
                "value": fields.get("priority", "未指定"),
                "inline": True,
            },
            {
                "name": "マイルストーン",
                "value": fields.get("milestone", "未指定"),
                "inline": True,
            },
            {
                "name": "発生バージョン",
                "value": fields.get("versions", "未指定"),
                "inline": True,
            },
            {
                "name": "期限日",
                "value": fields.get("due_date", "未指定"),
                "inline": True,
            },
        ] if e.get("value")]

    @staticmethod
    def create_fields(data):
        content = data["content"]

        def _parse_some_versions(content_, key):
            m = content_[key]
            if m:
                # 1番目決め打ち
                return m[0]["name"]
            return None

        return {
            "issue_type": content["issueType"].get("name"),
            "assignee": content.get("assignee"),
            "priority": content["priority"].get("name"),
            "milestone": _parse_some_versions(content, "milestone"),
            "versions": _parse_some_versions(content, "versions"),
            "due_date": content.get("dueDate"),
        }
