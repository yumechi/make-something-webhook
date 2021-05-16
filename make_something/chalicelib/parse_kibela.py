from typing import Dict, List, Any, Optional
import os
from abc import ABC, abstractmethod


def create_post_body(data) -> Dict[str, Any]:
    """
    kibela用の投稿ボディを作る。
    アクションによって、jsonモデルが大きく異なるので、それっぽい単位でパースする。

    未対応のtypeの場合はValueErrorを返す。
    kibelaの場合はresource_typeとactionのペアで決まる。
    https://support.kibe.la/hc/ja/articles/360035043592-Outgoing-Webhook%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6

    Args:
        data (Dict[str, Any]): リクエストデータ

    Returns:
        Dict[str, Any]: リクエスト用ボディ
    """

    action_type = data["action"]
    resource = data["resource_type"]

    if (action_type, resource) == ("send", "test"):
        return {}

    mp = {
        "blog": {
            "create": CreateBlog,
            "update": UpdateBlog,
            "delete": DeleteBlog,
        },
        "wiki": {
            "create": CreateWiki,
            "update": UpdateWiki,
            "delete": DeleteWiki,
        },
        "comment": {
            "create": CreateComment,
            "update": UpdateComment,
            "delete": DeleteComment,
        },
        "comment_reply": {
            "create": CreateReply,
            "update": UpdateReply,
            "delete": DeleteReply,
        },
    }
    cl = mp.get(resource, {}).get(action_type, {})
    if not cl:
        msg = f"Unknown type: action_type={action_type}, resource={resource}"
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
            "username": "kibela webhook",
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


class Article(ParseMixin):
    """
    Blog, Wikiの共通ロジック
    """

    def __init__(self, data):
        resource = data["resource_type"]
        action_user = data["action_user"]
        self.data = data[resource]
        self.user = action_user

    def get_title_url(self) -> str:
        url = self.data["url"] or ""
        return url

    def get_title(self) -> str:
        url = self.data["title"] or ""
        return url

    def get_username(self) -> str:
        user = self.user["account"]
        return user

    @staticmethod
    def get_author(content: Dict[str, Any]) -> Optional[str]:
        """
        公式ドキュメントを見ていると author と authors の両方が入る可能性がある。
        よって両対応にするため、吸収する。

        Returns:
            (Optional[str]): 記事の編集者
        """
        if "author" in content:
            author = content.get("author")
            return author.get("account")
        if "authors" in content:
            authors = content.get("authors")
            return ", ".join([author.get("account") for author in authors])
        return ""


class Blog(Article):
    """
    Blog用のパースロジック
    """

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        fields = []
        data = self.data
        author = self.get_author(data)
        if author:
            fields.append(
                {
                    "name": "記事の作成者",
                    "value": author,
                    "inline": True,
                }
            )
        extra_fields = self.get_extra_fields()
        if extra_fields:
            fields.extend(extra_fields)
        return fields

    def get_extra_fields(self) -> List[Dict[str, Any]]:
        """
        記事情報で他に追加するものがあればここに実装する
        """
        return []


class CreateBlog(Blog):
    BASE_DESCRITION_MESSAGE = "記事が作成されました"

    def get_description(self) -> str:
        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        return content


class UpdateBlog(Blog):
    BASE_DESCRITION_MESSAGE = "記事が更新されました"

    def get_description(self) -> str:
        content = self.data["content_diff"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        # diff なので diff 表示に
        return f"```diff\n{content}\n```"


class DeleteBlog(Blog):
    BASE_DESCRITION_MESSAGE = "記事が削除されました"

    def get_description(self) -> str:
        return ""


class Wiki(Article):
    """
    Wiki用のパースロジック
    """

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        fields = []
        data = self.data
        author = self.get_author(data)

        if author:
            fields.append(
                {
                    "name": "記事の作成者",
                    "value": author,
                    "inline": True,
                }
            )
        extra_fields = self.get_extra_fields()
        if extra_fields:
            fields.extend(extra_fields)
        return fields

    def get_extra_fields(self) -> List[Dict[str, Any]]:
        """
        記事情報で他に追加するものがあればここに実装する
        """
        return []


class CreateWiki(Wiki):
    BASE_DESCRITION_MESSAGE = "記事が作成されました"

    def get_description(self) -> str:
        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        return content


class UpdateWiki(Wiki):
    BASE_DESCRITION_MESSAGE = "記事が更新されました"

    def get_description(self) -> str:
        content = self.data["content_diff"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        # diff なので diff 表示に
        return f"```diff\n{content}\n```"


class DeleteWiki(Wiki):
    BASE_DESCRITION_MESSAGE = "記事が削除されました"

    def get_description(self) -> str:
        return ""


class CommentBase(ParseMixin):
    """
    Cooment, CommentReplyのベースクラス
    """

    def __init__(self, data):
        resource = data["resource_type"]
        action_user = data["action_user"]
        content = data[resource]
        if "blog" in content:
            article = content["blog"]
        elif "wiki" in content:
            article = content["wiki"]
        else:
            print(f"Can't find article: {resource}={content}")
            raise ValueError
        self.data = content
        self.article = article
        self.user = action_user

    def get_title_url(self) -> str:
        url = self.data["url"] or ""
        return url

    def get_title(self) -> str:
        # 記事のタイトルはarticle内にある
        url = self.article["title"] or ""
        return url

    def get_username(self) -> str:
        user = self.user["account"]
        return user

    @staticmethod
    def get_author(content: Dict[str, Any]) -> Optional[str]:
        """
        公式ドキュメントを見ていると author と authors の両方が入る可能性がある。
        よって両対応にするため、吸収する。

        Returns:
            (Optional[str]): 記事の編集者
        """
        if "author" in content:
            author = content.get("author")
            return author.get("account")
        if "authors" in content:
            authors = content.get("authors")
            return ", ".join([author.get("account") for author in authors])
        return ""

    def _parse(self) -> Optional[List[Dict[str, Any]]]:
        fields = []
        article = self.article
        author = self.get_author(article)

        if author:
            fields.append(
                {
                    "name": "記事の作成者",
                    "value": author,
                    "inline": True,
                }
            )
        extra_fields = self.get_extra_fields()
        if extra_fields:
            fields.extend(extra_fields)
        return fields

    def get_extra_fields(self) -> List[Dict[str, Any]]:
        """
        記事情報で他に追加するものがあればここに実装する
        """
        return []


class CreateComment(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが付きました"

    def get_description(self) -> str:
        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        return content


class UpdateComment(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが更新されました"

    def get_description(self) -> str:
        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        # コメントの場合 diff がないのでそのまま
        return content


class DeleteComment(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが削除されました"

    def get_description(self) -> str:
        return ""


class CreateReply(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが付きました"

    def get_description(self) -> str:
        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        return content


class UpdateReply(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが更新されました"

    def get_description(self) -> str:

        content = self.data["content_md"]
        if len(content) > 500:
            content = content[:500] + "（省略されました）"
        # コメントの場合 diff がないのでそのまま
        return content


class DeleteReply(CommentBase):
    BASE_DESCRITION_MESSAGE = "コメントが削除されました"

    def get_description(self) -> str:
        return ""
