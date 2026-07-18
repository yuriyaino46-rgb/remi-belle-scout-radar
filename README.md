# Remi Belle Scout Radar

公開情報だけを使い、面談候補の母集団形成を支援する人間参加型リサーチ基盤です。採用判断、DM、面談、契約を自動化しません。顔・センシティブ属性・健康状態・障害・性格を推測しません。

## 実装済み

- SQLiteを正本とする候補者、発見履歴、実行ログ管理
- X API v2の本人投稿優先検索（初期設定では課金防止のため停止）
- Instagram公式Graph APIによる公開ハッシュタグ検索
- TikTok / SHOWROOMの公開プロフィール逆引き用シード入力
- SNS URL優先の重複排除。名前は重複判定に不使用
- S級！！を厳格にした仮優先度、B・要確認を残す広い収集
- 対象外候補を削除せず理由・再確認優先度とともに保存
- 指定タブへのGoogle Sheets同期
- 成功、0件、部分失敗、未更新URLを必ず出すJSON/標準出力レポート
- JST 12:00 / 17:00 / 20:00のGitHub Actions定時実行

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
cp seeds/public_profiles.example.json seeds/public_profiles.json
remibelle-radar init-db
pytest
remibelle-radar run --no-sheets
```

Google CloudでSheets APIを有効化し、サービスアカウントを作成します。対象スプレッドシートをサービスアカウントのメールアドレスに「編集者」として共有し、`.env` にスプレッドシートIDとJSON鍵へのパスを設定してください。初回同期時に次のタブがなければ作成します。

- 候補者マスター
- X Radar
- Instagram Radar
- TikTok Radar
- SHOWROOM Radar
- 対象外・保留
- 実行ログ

## 公開プロフィールの投入

`seeds/public_profiles.json` は配列です。`radar` は `TikTok Radar` または `SHOWROOM Radar` とし、本人プロフィール、lit.link、Linktree、SHOWROOMプロフィール等から確認した公開URLを記録します。本人が掲載したInstagramリンクは `instagram_status: "本人掲載リンク"`、見つからない場合はURLを空にして `未確認` とします。

この入力口は、規約上または技術上TikTokを直接検索できない環境でも、X・SHOWROOM・リンク集からの逆引きを監査可能な形で残すためのものです。取得経緯は `evidence` に必ず記録してください。

## 運用上の注意

- X、Instagram、TikTok、SHOWROOMの利用規約・API条件・レート制限を守ってください。
- 非公開情報、ログイン回避、アクセス制御回避、スクレイピング禁止領域は収集しません。
- スコアと優先度は面談候補整理用の仮評価です。採否や契約可能性を示しません。
- GitHub Actionsのキャッシュは永続DBとして強い保証がありません。本番はCloud Run + Cloud SQL/永続ボリューム、またはDBスナップショットのオブジェクトストレージ保存を推奨します。
- 候補者から削除・訂正依頼が来た場合の運用手順と、保存期間・アクセス権を別途定めてください。

## コマンド

```bash
remibelle-radar run             # 全Radar実行 + Sheets同期 + レポート
remibelle-radar run --no-sheets # ローカル検証
remibelle-radar export-json     # DB監査用出力
```
