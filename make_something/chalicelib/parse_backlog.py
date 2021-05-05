from typing import Dict, List, Any, Optional
import os
from abc import ABC, abstractmethod, abstractproperty


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
        1: CreateIssue,
        2: UpdateIssue,
        4: DeleteIssue,
        3: Comment,
        22: CreateMilestone,
        23: UpdateMilestone,
        24: DeleteMilestone,
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

    BASE_DESCRITION_MESSAGE = None

    def parse(self) -> Dict[str, Any]:
        """
        フックポイントとなる
        """

        # FIXME: ベースとなる文言は環境変数とかからとって変更可能にしておく
        base = {
            "username": "uchia",
            "content": self.base_description,
        }
        base.update(self.create_embeds())
        fields = self._parse()

        if fields:
            base["embeds"][0]["fields"] = fields
        return base

    @property
    def base_description(self) -> str:
        return self.BASE_DESCRITION_MESSAGE or "新しい通知です"

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
    """
    issueのベースとなるクラス。
    Create, Updateは基本的にこっちだけ使う。
    """

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


class CreateIssue(Issue):
    BASE_DESCRITION_MESSAGE = "課題を作成しました"


class UpdateIssue(Issue):
    BASE_DESCRITION_MESSAGE = "課題を更新しました"


class DeleteIssue(Issue):
    """
    削除時のIssue用クラス。
    登録時と入ってくるデータが異なるので、元のIssueクラスを継承して上書きする。
    """

    BASE_DESCRITION_MESSAGE = "課題を削除しました"

    def __init__(self, data):
        self.data = data

    def get_title(self) -> str:
        project_prefix = os.environ.get("PROJECT_PREFIX")
        issue_id = self.data["content"]["id"]
        return f"{project_prefix}-{issue_id}"

    def get_description(self) -> str:
        return ""

    def _parse(self):
        """
        削除時はfieldsとして追加できる情報がないので、空リストを返す。
        """
        return []


class Comment(ParseMixin):
    """
    コメント用のクラス。
    大体Issueと同じ実装になってしまったが、いったんこのままにしておく。

    descriptionはコメントを追加しておく。
    """

    BASE_DESCRITION_MESSAGE = "コメントを追加しました"

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
        content = self.data["content"]
        return content.get("comment", {}).get("content", "説明なし")

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


class Milestone(ParseMixin):
    def __init__(self, data):
        self.data = data

    def get_title_url(self) -> str:
        """
        検索画面を返す。
        {base_url}/find/{project_prefix}??projectId={project_id}&fixedVersionId={version_id}
        """

        def _int(e):
            try:
                return int(e)
            except ValueError:
                return None
            except Exception as e:
                # TODO: エラーログはもう少しまじめに出す。
                print("idに数値以外が入ってきている")
                return None


        base_url = os.environ.get("BACKLOG_BASE_URL")
        project_prefix = os.environ.get("PROJECT_PREFIX")

        project = self.data.get("project", {})
        content = self.data.get("content", {})
        project_id = project.get("id", None)
        milistone_id = content.get("id", None)

        # project_id, milistone_idが取れる場合は検索画面へ飛ばす。そうでない場合はプロジェクトトップへ。
        if _int(project_id) and _int(milistone_id):
            return f"{base_url}/find/{project_prefix}?projectId={project_id}&fixedVersionId={milistone_id}"
        return f"{base_url}/projects/{project_prefix}"

    def get_title(self) -> str:
        return self.data["content"].get("name", "名称無し")

    def get_username(self) -> str:
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self) -> str:
        # TODO: アップデート時が雑かも
        return self.data["content"].get("description", "説明なし")

    def _parse(self):
        content = self.data
        return [
            e
            for e in [
                {
                    "name": "開始日",
                    "value": content.get("start_date"),
                    "inline": True,
                },
                {
                    "name": "終了日",
                    "value": content.get("reference_date"),
                    "inline": True,
                },
            ]
            if e.get("value")
        ]


class CreateMilestone(Milestone):
    BASE_DESCRITION_MESSAGE = "マイルストーンを作成しました"

class UpdateMilestone(Milestone):
    BASE_DESCRITION_MESSAGE = "マイルストーンを更新しました"

class DeleteMilestone(Milestone):
    BASE_DESCRITION_MESSAGE = "マイルストーンを削除しました"
