# eql-ja

EverQuest Legends 日本語化サポートスクリプト

## 手順

1. `eqstr_us.txt`を`eqstr_jp.txt`にコピーしておく
2. `eqstr_jp.txt`を和訳する
3. `eqstr.py modified`で翻訳した差分を`eqstr_mod.txt`に抽出する
4. アップデートがあったら`eqstr.py merge`で`eqstr_mod.txt`を`eqstr_us.txt`にマージして`eqstr_jp.txt`を作る
