#!/usr/bin/env -S python3
# SPDX-License-Identifier: MIT
# Copyright 2026 hirmiura (https://github.com/hirmiura)
"""dbstr形式のファイルを操作する"""

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

logger = logging.getLogger(__name__)


def pargs() -> argparse.Namespace:
    """コマンドライン引数を処理する

    Returns:
        argparse.Namespace: 処理した引数

    """
    parser = argparse.ArgumentParser(description="dbstr形式のファイルを操作する")

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
        default="dbstr_mod.txt",
        help="マージ元入力ファイル",
    )
    parser.add_argument(
        "-t",
        "--to",
        nargs="?",
        type=str,
        default="dbstr_us.txt",
        help="マージ先入力ファイル",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        type=str,
        default="dbstr_jp.txt",
        help="出力ファイル",
    )
    return parser


def command_merge(args: argparse.Namespace) -> None:
    """mergeコマンド"""
    logger.debug("[pargs] from:   %s", args.from_)
    logger.debug("[pargs] to:     %s", args.to)
    logger.debug("[pargs] output: %s", args.output)
    with open_input(args.from_) as f:
        es_f = Dbstr.load(f)
    with open_input(args.to) as f:
        es_t = Dbstr.load(f)
    es_result = es_t.merge(es_f)
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
        default="dbstr_jp.txt",
        help="比較先の入力ファイル",
    )
    parser.add_argument(
        "-b",
        "--base",
        nargs="?",
        type=str,
        default="dbstr_us.txt",
        help="比較元の入力ファイル",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        type=str,
        default="dbstr_mod.txt",
        help="出力ファイル",
    )
    return parser


def command_modified(args: argparse.Namespace) -> None:
    """modifiedコマンド"""
    logger.debug("[pargs] modified: %s", args.modified)
    logger.debug("[pargs] base:     %s", args.base)
    logger.debug("[pargs] output:   %s", args.output)
    with open_input(args.modified) as f:
        es_modi = Dbstr.load(f)
    with open_input(args.base) as f:
        es_base = Dbstr.load(f)
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


type DbstrDataType = dict[tuple[int, int], tuple[str, int]]


class Dbstr:
    """dbstr形式のデータを表すクラス"""

    def __init__(self, data: DbstrDataType):
        assert data is not None
        self.data = copy.deepcopy(data)
        logger.debug("[Dbstr] 要素数: %d", len(data))

    @staticmethod
    def load(input: TextIO) -> Dbstr:
        assert input
        data: DbstrDataType = {}
        # データの処理
        for line in input:
            n1, n2, rest = line.split("^", 2)
            rest = rest.rstrip("\r\n")
            t, n3, _ = rest.rsplit("^", 2)
            # logger.debug("[Dbstr] %s, %s, %s, %s", n1, n2, t, n3)
            data[(int(n1), int(n2))] = (t, int(n3))
        return Dbstr(data)

    def save(self, output: TextIO):
        assert output
        # データの処理
        keys = sorted(self.data.keys(), key=lambda x: (x[0], x[1]))
        for k in keys:
            output.write(f"{str(k[0])}^{str(k[1])}^{self.data[k][0]}^{str(self.data[k][1])}^\n")

    def merge(self, other: Dbstr) -> Dbstr:
        """他のEqstrを自身にマージした新しいオブジェクトを返す

        Args:
            other (Eqstr): 統合するオブジェクト

        Returns:
            Eqstr: 統合されたオブジェクト

        """
        assert other

        result: DbstrDataType = copy.deepcopy(self.data)
        for k in other.data:
            if not (k in self.data and self.data[k] == other.data[k]):
                result[k] = other.data[k]

        return Dbstr(result)

    def modified(self, other: Dbstr) -> Dbstr:
        """他のEqstrと比較して、自身から変更されている列を抜き出す

        Args:
            other (Eqstr): 比較対象

        Returns:
            Eqstr: 変更箇所を集めたオブジェクト

        """
        assert other

        result: DbstrDataType = {}
        for k in self.data:
            if k in other.data:
                if self.data[k] != other.data[k]:
                    result[k] = self.data[k]
            else:
                logging.warning("比較元にないデータがあります: %s", k)
        return Dbstr(result)


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
