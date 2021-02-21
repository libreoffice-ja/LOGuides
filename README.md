LibreOffice ドキュメンテーション 翻訳・査読リポジトリ
============================================

これは何？
--------

翻訳ツール[OmegaT](https://omegat.org/ja/)を使って、[LibreOfficeのドキュメント](https://documentation.libreoffice.org/en/english-documentation/)を翻訳、査読するための作業用リポジトリです。

作業に参加するには?
----------------

作業には[OmegaT](https://omegat.org/ja/)とGithubアカウントが必要になります。事前に[OmegaTのダウンロード/インストール](https://omegat.org/ja/download)とGithubアカウントの取得をお願いします。

そして、Writerガイドの変更を反映させるには、このリポジトリの書き込み権限が必要になるので、[LibreOffice日本語メーリングリスト](https://ja.libreoffice.org/get-help/mailing-lists/)の
ja-discussまたは[Telegramチャット](https://t.me/liboja)で書き込み権限について相談していただくか、Issueに書き込んでください。

odtファイルを編集するためプルリクエストは受け付けていません。

OmegaTの設定方法と作業方法
----------------------

### プラグインのインストール

OmegaTには、[みんなの自動翻訳@Textra](https://mt-auto-minhon-mlt.ucri.jgn-x.jp/)を利用するためのプラグイン[omegat-textra-plugin](https://github.com/miurahr/omegat-textra-plugin)とMarkdown文書などを翻訳するための[Okapi Filters Plugin for OmegaT](https://bintray.com/okapi/Distribution/OmegaT_Plugin)をそれぞれインストールしてください。

インストール方法は、プログラム本体を格納しているフォルダ内のpluginsフォルダか、設定ファイルを保存しているフォルダ内のpluginsフォルダに、zipファイルを展開して中にあるjarファイルを移動するだけです。

プラグインがインストールされたか確認をするには、OmegaTを開いて、メニュー[設定] > [環境設定]を開き、環境設定ダイアログの「プラグイン」を選択します。認識されたプラグイン一覧が表示されるので、ここにプラグインがあるか見てください。

### omegat-textra-pluginの設定

OmegaTを開き、メニュー[設定] > [環境設定]を開きまます。環境設定ダイアログの「機械翻訳」を選択します。利用できる機械翻訳リストの一番下に「Textra Powerd by NICT」という項目があるので選択して、「設定」ボタンを押します。

以下のように設定をすれば、LibreOfficeの翻訳に特化した機械翻訳が利用できます。

* NICT TexTra(nonprofit)
* ユーザーID: libreoffice
* API Key: dd2624cc7c16e8fb1f39b2d550a06ea005ff06f7f
* API Secret: 8eccf33e079c2e648b2fc700bc6263c2
* 翻訳モード: Custom: c-1465_en_ja

### リポジトリを使うための設定

OmegaTを開き、メニュー[設定] > [環境設定]を開きます。環境設定ダイアログにある「チーム」に自分のアカウント名を入力しておきます。

続いて、メニュー[プロジェクト] > [チームプロジェクトをダウンロード]を選択し、リポジトリ名を入力します。(SSHアクセスはOmegaTが対応していないので、HTTPで入力してください。)

* リポジトリ名: https://github.com/libreoffice-ja/LOGuides.git
* ローカルプロジェクトフォルダー: （入力しない・自動的に入力される）

確定ボタンを押すとローカルプロジェクトフォルダーの場所にリポジトリがクローンされます。クローンには時間がかかるので気長にお待ちください。

クローンが終われば通常のOmegaTでの翻訳と同じように使ってください。使い方については以下のドキュメントを参考にしてください。

* CATビギナーのためのOmegaT入門 - HackMD: https://hackmd.io/@omegat/rJU6Pl5mw#
* OmegaT - The CAT パワーツール - HackMD: https://hackmd.io/@omegat/HJ1_x15Vw#

保存をすれば、リポジトリにそのつどコミットとプッシュされるので作業は全部記録されます。
このとき、変更者のIDも記録されるので、以前のドキュメントにあったメモを書く必要はありません。

注意: 2020年3月現在、Writer6.4ガイドは、Google翻訳を使った下訳状態ですので、これを全部書き換える必要があります。


連絡先
-----

* [LibreOffice日本語メーリングリスト](https://ja.libreoffice.org/get-help/mailing-lists/)のja-discuss
* Telegram(チャット): https://t.me/liboja

