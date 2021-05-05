# make-something-bot
オンラインで何かする

Backlog, kibelaの通知をDiscordに流そうというチャレンジ。

## 対応状況
### Backlog

対応しているイベントは下記。[公式ドキュメント](https://developer.nulab.com/ja/docs/backlog/api/2/get-recent-updates/#%E3%83%AC%E3%82%B9%E3%83%9D%E3%83%B3%E3%82%B9%E8%AA%AC%E6%98%8E)のtypeによって分類している。

| type | action                         | status | priority |
| ---- | ------------------------------ | ------ | -------- |
| 1    | 課題の追加                     | 〇     | high     |
| 2    | 課題の更新                     | 〇     | high     |
| 3    | 課題にコメント                 | 〇     | high     |
| 4    | 課題の削除                     | 〇     | high     |
| 5    | Wikiを追加                     |        | low      |
| 6    | Wikiを更新                     |        | low      |
| 7    | Wikiを削除                     |        | low      |
| 8    | 共有ファイルを追加             |        | low      |
| 9    | 共有ファイルを更新             |        | low      |
| 10   | 共有ファイルを削除             |        | low      |
| 11   | Subversionコミット             |        | low      |
| 12   | GITプッシュ                    |        | low      |
| 13   | GITリポジトリ作成              |        | low      |
| 14   | 課題をまとめて更新             | 〇  | medium   |
| 15   | ユーザーがプロジェクトに参加   |        | low      |
| 16   | ユーザーがプロジェクトから脱退 |        | low      |
| 17   | コメントにお知らせを追加       |        | low      |
| 18   | プルリクエストの追加           |        | low      |
| 19   | プルリクエストの更新           |        | low      |
| 20   | プルリクエストにコメント       |        | low      |
| 21   | プルリクエストの削除           |        | low      |
| 22   | マイルストーンの追加           | 〇     | medium   |
| 23   | マイルストーンの更新           | 〇     | medium   |
| 24   | マイルストーンの削除           | 〇     | medium   |
| 25   | グループがプロジェクトに参加   |        | low      |
| 26   | グループがプロジェクトから脱退 |        | low      |

### Kibela

| resource_type | action | action                         | status | priority |
| ------------- | ------ | ------------------------------ | ------ | -------- |
| blog          | create | 共同編集が「無効」な記事の投稿 | 〇     | medium   |
| blog          | update | 共同編集が「無効」な記事の更新 | 〇     | medium   |
| blog          | delete | 共同編集が「無効」な記事の削除 | 〇     | medium   |
| wiki          | create | 共同編集が「有効」な記事の投稿 | 〇     | medium   |
| wiki          | update | 共同編集が「有効」な記事の更新 | 〇     | medium   |
| wiki          | delete | 共同編集が「有効」な記事の削除 | 〇     | medium   |
| comment       | create | コメントの投稿                 | 〇     | medium   |
| comment       | update | コメントの更新                 | 〇     | medium   |
| comment       | delete | コメントの削除                 | 〇     | medium   |
| comment_reply | create | コメント返信の投稿             | 〇     | medium   |
| comment_reply | update | コメント返信の更新             | 〇     | medium   |
| comment_reply | delete | コメント返信の削除             | 〇     | medium   |
| send          | test   | テスト                         | 〇     | high     |

## TODO

* [ ] テストを書く
* [ ] リトライを楽にする仕組み（S3にボディ書き出すとか）
* [ ] エラーパターンをもう少し真面目に
* [ ] もう少し柔軟に投稿ユーザー指定を
