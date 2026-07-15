#!/usr/bin/env -S python3
# SPDX-License-Identifier: MIT
# Copyright 2026 hirmiura (https://github.com/hirmiura)
"""eqstr形式のファイルを操作する"""

from __future__ import annotations

import argparse
import copy
import io
import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    # このブロック内は実行時には無視されます
    from _typeshed import OpenTextMode


DEFAULT_HEADER: str = "EQST0004"

logger = logging.getLogger(__name__)


def pargs() -> argparse.Namespace:
    """コマンドライン引数を処理する

    Returns:
        argparse.Namespace: 処理した引数

    """
    parser = argparse.ArgumentParser(description="eqstr形式のファイルをマージする")

    # サブコマンドを管理するオブジェクトを作成
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    subparsers.required = True  # コマンドを必須に

    # --- merge コマンドの設定 ---
    comparser_merge(subparsers)
    # --- modified コマンドの設定 ---
    comparser_modified(subparsers)

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()
    args.func(args)

    return args


def comparser_merge(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """mergeコマンドのパーサーを設定"""
    parser = subparsers.add_parser(
        "merge",
        help="マージします",
        add_help=False,
        description="2つのファイルを統合します。入出力は分離しているので同じファイルを指定しても構いません。",
    )
    parser.set_defaults(func=command_merge)
    parser.add_argument(
        "-f",
        "--from",
        dest="from_",
        metavar="FROM",
        nargs="?",
        type=str,
        default="eqstr_jp.txt",
        help="マージ元入力ファイル",
    )
    parser.add_argument(
        "-t",
        "--to",
        nargs="?",
        type=str,
        default="eqstr_us.txt",
        help="マージ先入力ファイル",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        type=str,
        default="-",
        help="出力ファイル",
    )
    return parser


def command_merge(args: argparse.Namespace) -> None:
    """mergeコマンド"""
    logger.debug("[pargs] from:   %s", args.from_)
    logger.debug("[pargs] to:     %s", args.to)
    logger.debug("[pargs] output: %s", args.output)
    with open_input(args.from_) as f:
        es_modi = Eqstr.load(f)
    with open_input(args.to) as f:
        es_base = Eqstr.load(f)
    es_result = es_modi.merge(es_base)
    with open_output(args.output) as f:
        es_result.save(f)


def comparser_modified(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """modifiedコマンドのパーサーを設定"""
    parser = subparsers.add_parser(
        "modified",
        help="変更箇所を抽出します",
        add_help=False,
        description="2つのファイルから変更箇所を抽出します。入出力は分離しているので同じファイルを指定しても構いません。",
    )
    parser.set_defaults(func=command_modified)
    parser.add_argument(
        "-m",
        "--modified",
        nargs="?",
        type=str,
        default="eqstr_jp.txt",
        help="比較先の入力ファイル",
    )
    parser.add_argument(
        "-b",
        "--base",
        nargs="?",
        type=str,
        default="eqstr_us.txt",
        help="比較元の入力ファイル",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        type=str,
        default="-",
        help="出力ファイル",
    )
    return parser


def command_modified(args: argparse.Namespace) -> None:
    """modifiedコマンド"""
    logger.debug("[pargs] modified: %s", args.modified)
    logger.debug("[pargs] base:     %s", args.base)
    logger.debug("[pargs] output:   %s", args.output)
    with open_input(args.modified) as f:
        es_modi = Eqstr.load(f)
    with open_input(args.base) as f:
        es_base = Eqstr.load(f)
    es_result = es_modi.modified(es_base)
    with open_output(args.output) as f:
        es_result.save(f)


@contextmanager
def open_input(
    path_str: str,
    mode: OpenTextMode = "r",
    encoding: str = "utf-8-sig",
    newline: str = "",
    **kwargs,
):
    """'-' なら sys.stdin を返し、それ以外はファイルを開くコンテキストマネージャ"""
    if path_str == "-":
        yield sys.stdin
    else:
        # ここで Path オブジェクトの操作（存在チェック等）も可能
        try:
            with Path(path_str).open(mode, encoding=encoding, newline=newline, **kwargs) as f:
                yield f
        except FileNotFoundError:
            logging.error("ファイルが存在しません: %s", path_str)
            sys.exit(1)
        except PermissionError:
            logging.error("権限がありません: %s", path_str)
            sys.exit(1)
        except Exception as e:
            logging.error("なんらかの例外が発生しました: %s %s", path_str, e)
            sys.exit(1)


@contextmanager
def open_output(
    path_str: str,
    mode: OpenTextMode = "w",
    encoding: str = "utf-8",
    newline: str = "\r\n",
    **kwargs,
):
    """'-' なら sys.stdout を返し、それ以外はファイルを開くコンテキストマネージャ"""
    if path_str == "-":
        yield sys.stdout
    else:
        # ここで Path オブジェクトの操作（存在チェック等）も可能
        try:
            with Path(path_str).open(mode, encoding=encoding, newline=newline, **kwargs) as f:
                yield f
        except FileNotFoundError:
            logging.error("ファイルが存在しません: %s", path_str)
            sys.exit(1)
        except PermissionError:
            logging.error("権限がありません: %s", path_str)
            sys.exit(1)
        except Exception as e:
            logging.error("なんらかの例外が発生しました: %s %s", path_str, e)
            sys.exit(1)


class Eqstr:
    """eqstr形式のデータを表すクラス"""

    def __init__(self, data: dict[int, str], header: str = DEFAULT_HEADER):
        assert data is not None
        assert header

        self.header = header
        if header != DEFAULT_HEADER:
            logger.warning("[Eqstr] 標準的ではないヘッダが使われています: %s", header)
        logger.debug("[Eqstr] ヘッダ: %s", self.header)

        self.data = copy.deepcopy(data)

        if 0 in data:
            num_in_real = len(data) - 1
            num_in_data = int(data[0])
            del self.data[0]
            if num_in_data != num_in_real:
                logger.warning(
                    "[Eqstr] 指定された要素数と実際の数が異なるため実際の数を使用します: %d != %d",
                    num_in_data,
                    num_in_real,
                )
        else:
            num_in_real = len(data)
        self.number = num_in_real
        logger.debug("[Eqstr] 要素数: %d", self.number)

    @staticmethod
    def load(input: TextIO) -> Eqstr:
        assert input
        data: dict[int, str] = {}
        # ヘッダの処理
        header = input.readline()
        header = header.rstrip("\r\n")
        if not header:
            raise SyntaxError("ヘッダがありません")
        # データの処理
        for line in input:
            n, t = line.split(" ", 1)
            t = t.rstrip("\r\n")
            data[int(n)] = t
        return Eqstr(data, header)

    def save(self, output: TextIO):
        assert output
        # ヘッダの処理
        output.write(f"{self.header}\n")
        # 要素数の処理
        output.write(f"0 {str(self.number)}\n")
        # データの処理
        keys = sorted(self.data.keys())
        for k in keys:
            output.write(f"{str(k)} {self.data[k]}\n")

    def merge(self, other: Eqstr) -> Eqstr:
        """他のEqstrを自身にマージした新しいオブジェクトを返す

        Args:
            other (Eqstr): 統合するオブジェクト

        Returns:
            Eqstr: 統合されたオブジェクト

        """
        assert other

        result: dict[int, str] = copy.deepcopy(self.data)
        for k in other.data:
            if not (k in self.data and self.data[k] != other.data[k]):
                result[k] = other.data[k]

        return Eqstr(result)

    def modified(self, other: Eqstr) -> Eqstr:
        """他のEqstrと比較して、自身から変更されている列を抜き出す

        Args:
            other (Eqstr): 比較対象

        Returns:
            Eqstr: 変更箇所を集めたオブジェクト

        """
        assert other

        result: dict[int, str] = {}
        for k in self.data:
            if k in other.data and self.data[k] != other.data[k]:
                result[k] = self.data[k]
        return Eqstr(result)


def main() -> int:
    """メイン関数

    Returns:
        int: 成功時は0を返す

    """
    # 引数処理
    pargs()
    return 0


if __name__ == "__main__":
    if os.name == "nt":
        # Windows対策
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", newline="\r\n")
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\r\n")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", newline="\r\n")

    # loggingの設定
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    logging.addLevelName(logging.WARNING, "W")
    logging.addLevelName(logging.INFO, "I")
    logging.addLevelName(logging.DEBUG, "D")

    sys.exit(main())
