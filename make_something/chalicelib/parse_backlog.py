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
        1: CreateIssue,
        2: UpdateIssue,
        4: DeleteIssue,
        3: Comment,
        22: CreateMilestone,
        23: UpdateMilestone,
        24: DeleteMilestone,
        14: MultiUpdateIssue,
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

    BASE_DESCRITION_MESSAGE: Optional[str] = None

    def parse(self) -> Dict[str, Any]:
        """
        フックポイントとなるパース処理。
        ベースとなるものをセットしたうえで、embedsを継承先で実装し、追加できるようにしておく。

        Returns:
            (Dict[str, Any]): DiscordにPostする実際のBody
        """

        # FIXME: ベースとなる文言は環境変数とかからとって変更可能にしておく
        base = {
            "username": "backlog webhook",
            "content": self.base_description,
        }
        base.update(self.create_embeds())
        fields = self._parse()

        if fields:
            base["embeds"][0]["fields"] = fields
        return base

    @property
    def base_description(self) -> str:
        """
        embedsの外側に表示されるベースとなるdescritionを返す。
        BASE_DESCRITION_MESSAGEを継承先で上書きし、それぞれだしたい表示文言に変更する。

        Returns:
            (str): ベースのdescription
        """
        return self.BASE_DESCRITION_MESSAGE or "新しい通知です"

    @abstractmethod
    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        """
        fieldsをパースして返す。

        Returns:
            (Optional[Dict[str, Any]]): fieldsのベースとなるデータ
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
        issue_id = self.data["content"]["key_id"]
        return f"{base_url}/view/{project_prefix}-{issue_id}"

    def get_title(self) -> str:
        return self.data["content"].get("summary", "タイトルなし")

    def get_username(self) -> str:
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self) -> str:
        description = self.data["content"].get("description", "説明なし")
        if len(description) > 500:
            description = description[:500] + "（省略されました）"
        return description

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
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
    def create_fields(data) -> Dict[str, Any]:
        content = data["content"]

        def _parse_some_versions(content_, key):
            m = content_[key]
            if m:
                # 1番目決め打ち
                return m[0]["name"]
            return None

        def _get_dict(cont, key):
            elem = cont.get(key, {})
            if not elem:
                return {}
            return elem

        return {
            "issue_type": _get_dict(content, "issueType").get("name"),
            "assignee": _get_dict(content, "assignee").get("name") or "未指定",
            "priority": _get_dict(content, "priority").get("name"),
            "status": content.get("status", {}).get("name"),
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
        issue_id = self.data["content"]["key_id"]
        return f"{project_prefix}-{issue_id}"

    def get_description(self) -> str:
        return ""

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
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
        issue_id = self.data["content"]["key_id"]
        return f"{base_url}/view/{project_prefix}-{issue_id}"

    def get_title(self) -> str:
        return self.data["content"].get("summary", "タイトルなし")

    def get_username(self) -> str:
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self) -> str:
        content = self.data["content"]
        description = content.get("comment", {}).get("content", "説明なし")
        if len(description) > 500:
            description = description[:500] + "（省略されました）"
        return description

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
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
    def create_fields(data) -> Dict[str, Any]:
        content = data["content"]

        def _parse_some_versions(content_, key):
            m = content_[key]
            if m:
                # 1番目決め打ち
                return m[0]["name"]
            return None

        def _get_dict(cont, key):
            elem = cont.get(key, {})
            if not elem:
                return {}
            return elem

        return {
            "issue_type": _get_dict(content, "issueType").get("name"),
            "assignee": _get_dict(content, "assignee").get("name") or "未指定",
            "priority": _get_dict(content, "priority").get("name"),
            "status": content.get("status", {}).get("name"),
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

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
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


class MultiUpdateIssue(ParseMixin):
    BASE_DESCRITION_MESSAGE = "課題を複数更新しました"

    def __init__(self, data):
        self.data = data
        # 複数更新時に入ってくるコメント
        self.comment = None

    def get_title_url(self) -> str:
        """
        課題の複数更新の場合は、いったんタイトルのリンクはプロジェクトのトップに飛ばす。
        """
        base_url = os.environ.get("BACKLOG_BASE_URL")
        project_prefix = os.environ.get("PROJECT_PREFIX")
        return f"{base_url}/projects/{project_prefix}"

    def get_title(self) -> str:
        # description側で作業するので空文字にする
        return ""

    def get_username(self) -> str:
        return self.data["createdUser"].get("name", "名前なし")

    def get_description(self) -> str:
        """
        更新したissueをリスト形式で出す。
        TODO: コメントがchangesに入ってこずにissue側に入ってくるのでつらい。インスタンス変数に書いて逃げることにする。
        """

        def _base_issue_url():
            base_url = os.environ.get("BACKLOG_BASE_URL")
            project_prefix = os.environ.get("PROJECT_PREFIX")
            return f"{base_url}/view/{project_prefix}"

        project_prefix = os.environ.get("PROJECT_PREFIX")
        link_content = self.data["content"]["link"]
        issue_url = _base_issue_url()
        msg_list = []
        for d in link_content:
            issue_id = d["key_id"]
            issue_title = d["title"]
            comment = d.get("comment", {}).get("content")
            if comment:
                self.comment = comment
            msg = f"[{project_prefix}-{issue_id} {issue_title}]({issue_url}-{issue_id})"
            msg_list.append(msg)
        return "\n".join(msg_list) or "内容無し"

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        fields = []
        if self.comment:
            comment = self.comment
            if len(comment) > 300:
                comment = comment[:300] + "（省略されました）"
            fields.append(
                {
                    "name": "コメント",
                    "value": comment,
                    "inline": True,
                }
            )

        changes = self.data["content"]["changes"]
        if changes:
            for d in changes:
                # TODO: 名称に追従するのは疲れるのでいったんkey名で…
                name = d["field"]
                value = d.get("new_value", "変更有")
                fields.append(
                    {
                        "name": name,
                        "value": value,
                        "inline": True,
                    }
                )

        return fields
