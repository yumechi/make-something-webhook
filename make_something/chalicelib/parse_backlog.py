from typing import Dict, List, Any, Optional
import os
from abc import ABC, abstractmethod


def create_post_body(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backlog用の投稿ボディを作る。
    typeによって、jsonモデルが大きく異なるので、それっぽい単位でパースする。

    未対応のtypeの場合はValueErrorを返す。
    typeはこのドキュメントを参照。https://developer.nulab.com/ja/docs/backlog/api/2/get-recent-updates/#%E3%83%AC%E3%82%B9%E3%83%9D%E3%83%B3%E3%82%B9%E8%AA%AC%E6%98%8E

    Args:
        data (Dict[str, Any]): リクエストデータ

    Returns:
        Dict[str, Any]: リクエスト用ボディ
    """

    action_type = data["type"]
    mp = {
        1: Issue,
        2: Issue,
        4: DeleteIssue,
    }
    cl = mp.get(action_type)
    if not cl:
        msg = f"Unknown type: {action_type}"
        print(msg)
        raise ValueError(msg)
    return cl(data).parse()


class ParseMixin(ABC):
    """
    Backlog用の投稿ボディベースを司るMixin。
    いろいろインターフェース的に使うものを定義する。

    ベースとなるものは雑にこっちで作って、詳細は _parse の実装に任せる。
    実質的にself.dataにレスポンスデータが入っていることを前提にしている。
    """

    def parse(self) -> Dict[str, Any]:
        """
        フックポイントとなる
        """

        # FIXME: ベースとなる文言は環境変数とかからとって変更可能にしておく
        base = {
            "username": "uchia",
            "content": "新しい更新通知なのです。",
        }
        base.update(self.create_embeds())
        fields = self._parse()

        if fields:
            base["embeds"][0]["fields"] = fields
        return base

    @abstractmethod
    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        """
        fieldsをパースして返す。

        Returns:
            (Dict[str, Any]): fieldsのベースとなるデータ
        """
        return {}

    @abstractmethod
    def get_title_url(self) -> str:
        pass

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_username(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    def create_embeds(self) -> Dict[str, Any]:
        """
        embedsの中身をとりあえず生成する。
        絶対必須になるものだけを定義しておいて、
        継承先でフックして定義しなおす。

        Returns:
            (Dict[str, Any]): ベースとなるembeds
        """
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


class Issue(ParseMixin):
    def __init__(self, data):
        self.data = data

    def get_title_url(self) -> str:
        base_url = os.environ.get("BACKLOG_BASE_URL")
        project_prefix = os.environ.get("PROJECT_PREFIX")
        issue_id = self.data["content"]["id"]
        return f"{base_url}/view/{project_prefix}-{issue_id}"

    def get_title(self) -> str:
        return self.data["content"].get("summary", "タイトルなし")

    def get_username(self) -> str:
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self) -> str:
        return self.data["content"].get("description", "説明なし")

    def _parse(self):
        fields = self.create_fields(self.data)

        return [
            e
            for e in [
                {
                    "name": "種別",
                    "value": fields.get("issue_type"),
                    "inline": True,
                },
                {
                    "name": "担当者",
                    "value": fields.get("assignee"),
                    "inline": True,
                },
                {
                    "name": "優先度",
                    "value": fields.get("priority"),
                    "inline": True,
                },
                {
                    "name": "ステータス",
                    "value": fields.get("status"),
                    "inline": True,
                },
                {
                    "name": "マイルストーン",
                    "value": fields.get("milestone"),
                    "inline": True,
                },
                {
                    "name": "発生バージョン",
                    "value": fields.get("versions"),
                    "inline": True,
                },
                {
                    "name": "期限日",
                    "value": fields.get("due_date"),
                    "inline": True,
                },
            ]
            if e.get("value")
        ]

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
            "issue_type": content.get("issueType", {}).get("name"),
            "assignee": content.get("assignee") or "未指定",
            "priority": content.get("priority", {}).get("name"),
            "status": content.get("status").get("name"),
            "milestone": _parse_some_versions(content, "milestone"),
            "versions": _parse_some_versions(content, "versions"),
            "due_date": content.get("dueDate"),
        }


class DeleteIssue(Issue):
    """
    削除時のIssue用クラス。
    登録時と入ってくるデータが異なるので、元のIssueクラスを継承して上書きする。
    """

    def __init__(self, data):
        self.data = data

    def get_title(self) -> str:
        project_prefix = os.environ.get("PROJECT_PREFIX")
        issue_id = self.data["content"]["id"]
        return f"課題を削除しました: {project_prefix}-{issue_id}"

    def get_description(self) -> str:
        return ""

    def _parse(self):
        """
        削除時はfieldsとして追加できる情報がないので、空リストを返す。
        """
        return []
