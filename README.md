# README

## 使用方法

1. 環境セットアップ  
   [Hugo](https://gohugo.io/)をインストールすべきである。公式サイトから入手してインストールする方法を推奨する。  

2. ローカル開発環境の起動  
   リポジトリ直下で以下のコマンドを実行する。  
   ```
   hugo server
   ```  
   実行後に表示されるローカルホスト（例: http://localhost:1313/）へアクセスすると、プレビューが可能である。

3. 記事の作成・更新方法  
   - hugo new content posts/xxx.mdでMarkdownファイルを新規作成すべきである。  
   - ファイル保存後にブラウザを再読み込みすると、記事を即時にプレビューできる。  
   - 既存記事を更新した場合も同様にプレビューが反映される。

以上を遵守すべきである。HugoのバージョンやOS環境によって一部コマンドが異なる場合があるため、適宜修正するとよい。
なお、`hugo v0.145.0+extended+withdeploy darwin/arm64 BuildDate=2025-02-26T15:41:25Z VendorInfo=brew`で動作確認済みである。

## GitHub Pagesデプロイ
mainブランチへのpush時に自動的にHugoをビルドし、publicディレクトリ以下の内容がGitHub Pagesにデプロイされる。  
https://yusukeshimizu.github.io/blog/ にアクセスすると、公開されているページを確認できる。