# sage-residence-weather

VRChat ワールド Sage Residence の天気の小物が読むデータです。1日数回、GitHub Actions が更新します。

- データ: `weather.txt`（タブ区切り。地域ごとに1行で、7日分の天気コード、降水確率、最低気温、最高気温）
- 作り方: `build_weather.py`

出典：[気象庁ホームページ](https://www.jma.go.jp/bosai/forecast/)の天気予報を加工して作成。気象庁の公式なサービスではありません。正確な情報は気象庁の発表を確認してください。
