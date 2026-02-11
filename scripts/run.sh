#!/usr/bin/env fish
# TheAwase 実行スクリプト

set SCRIPT_DIR (dirname (status filename))
set PROJECT_DIR (dirname $SCRIPT_DIR)
set VENV_DIR ~/local/venv

# 仮想環境アクティベート
if test -f $VENV_DIR/bin/activate.fish
    source $VENV_DIR/bin/activate.fish
else
    echo "Error: Virtual environment not found at $VENV_DIR"
    exit 1
end

# プロジェクトディレクトリへ移動
cd $PROJECT_DIR

# メインルーチン実行
python -m theawase.main $argv
