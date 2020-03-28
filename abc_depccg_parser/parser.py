import typing
import pathlib
import io
import sys
import parsy

from . import tokenizer

parser: "depccg.parser.JapaneseCCGParser" = None

def generate_parser(
    model_path: pathlib.Path = None
    # pathlib.PurePosixPath("/...")
) -> "depccg.parser.JapaneseCCGParser" :
    from depccg.combinator import (
        HeadfinalCombinator,
        JaForwardApplication,
        JaBackwardApplication,
        JaGeneralizedForwardComposition0,
        # JaGeneralizedForwardComposition1,
        # JaGeneralizedForwardComposition2,
        JaGeneralizedBackwardComposition0,
        JaGeneralizedBackwardComposition1,
        JaGeneralizedBackwardComposition2,
        JaGeneralizedBackwardComposition3,
    )
    from depccg.parser import JapaneseCCGParser

    # 使う組み合わせ規則 headfinal_combinatorでくるんでください。
    binary_rules = [
        HeadfinalCombinator(r) 
        for r in {
            JaForwardApplication(),             # 順方向関数適用
            JaBackwardApplication(),            # 逆方向関数適用
            JaGeneralizedForwardComposition0(
                # 順方向関数合成 X/Y Y/Z -> X/Z
                '/', '/', '/', '>B'
            ),
            JaGeneralizedBackwardComposition0(
                # Y\Z X\Y -> X\Z
                '\\', '\\', '\\', '<B1'
            ),
            JaGeneralizedBackwardComposition1(
                # (X\Y)|Z W\X --> (W\Y)|Z
                '\\', '\\', '\\', '<B2'
            ),
            JaGeneralizedBackwardComposition2(
                # ((X\Y)|Z)|W U\X --> ((U\Y)|Z)|W
                '\\', '\\', '\\', '<B3'
            ),
            JaGeneralizedBackwardComposition3(
                # (((X\Y)|Z)|W)|U S\X --> (((S\Y)|Z)|W)|U
                '\\', '\\', '\\', '<B4'
            ),
        }
    ]

    # パーザのオプション
    kwargs = dict(
        # unary ruleを使いすぎないようにペナルティを与えます。
        unary_penalty = 0.1,
        #nbest=,
        binary_rules = binary_rules,
        # ルートのカテゴリがこれらに含まれる木のみ解析結果として出力します
        possible_root_cats = [
            "S[m]", "FRAG", "INTJP", "CP[f]", "CP[q]", 
            "S[imp]", "CP[t]", "LST", "CP-EXL"
        ],
        use_seen_rules = False,
        use_category_dict = False,
        # 長い文は諦める
        max_length = 250,
        # 一定時間内に解析が終了しない場合解析を諦める
        max_steps = 10000000,
        # 構文解析にGPUを使うかどうか？
        gpu = -1
    )

    # 設定ファイルとallennlpのモデルからパーザを初期化
    model_path_str: str = str(model_path)

    parser = JapaneseCCGParser.from_json(
        model_path_str + "/config_parser_abc.json", 
        model_path_str + "/model",
        **kwargs
    )

    return parser
# === END ===

def parse_doc(
    doc: typing.Iterable[str],
    is_to_tokenize: bool = False,
    batchsize: int = 16,
) -> typing.Tuple["parsed_trees", typing.Iterator[typing.Iterable[typing.Any]]]:
    from depccg.parser import JapaneseCCGParser
    import depccg.tokens
    global parser

    if not parser:
        parser = generate_parser()
    # === END IF ===
    
    doc_stripped: typing.Iterator[str] = filter(
        None,
        (sent.strip() for sent in doc)
    )

    doc_tagged: typing.Iterator[typing.Iterable[typing.Any]]
    doc_tokenized: typing.Iterator[typing.Iterable[typing.Any]]

    if is_to_tokenize:
        doc_tagged, doc_tokenized = tokenizer.tokenize(
            (
                tuple(word for word in sent.split(' '))
                for sent in doc_stripped
            )
        )
    else:
        doc_tokenized = list(doc_stripped)
        doc_tagged = depccg.tokens.annotate_XX(
            (
                tuple(word for word in sent.split(' '))
                for sent in doc_tokenized
            ),
            tokenize = is_to_tokenize
        )
    # === END IF ===
    print(doc_tokenized)
    parsed_trees = parser.parse_doc(
        doc_tokenized,
        batchsize = batchsize
    )
    
    return (parsed_trees, doc_tagged)
# === END ===

def dump_batch_parsed_others(
    parsed_trees,
    tokens_of_trees,
    output_format: str,
    lang: str,
    stream: typing.TextIO = sys.stdout,
):
    import depccg.printer
    
    # TODO: redirect to stream
    depccg.printer.print_(
        parsed_trees,
        tokens_of_trees,
        output_format,
        lang,
    )
# === END ===

def dump_parsed_ABCT(
    parsed,
    tokens,
    ID: str = "NONE",
    stream: typing.TextIO = sys.stdout,
) -> typing.NoReturn:
    for tree, prob in parsed:
        tree_enh = {
            "type": "ROOT",
            "cat": "TOP",
            "children": [
                {
                    "cat": "COMMENT",
                    "surf": f"{{probability={prob}}}"
                },
                tree.json(tokens = tokens),
                {
                    "cat": "ID",
                    "surf": str(ID)
                }
            ]
        }

        dump_tree_ABCT(tree_enh, stream)
        stream.write("\n")
    # === END FOR parsed ===
# === END ===

def print_parsed_ABCT(
    parsed,
    tokens,
    ID: str = "NONE"
) -> str:
    with io.StringIO() as sf:
        dump_parsed_ABCT(parsed, tokens, ID, stream = sf)
        return sf.getvalue()
    # === END WITH sf ===
# === END ====

def dump_tree_ABCT(tree: dict, stream: typing.TextIO) -> typing.NoReturn:
    cat = parse_cat_translate_TLG(tree["cat"])

    if "children" in tree.keys():
        stream.write(f"({cat}")

        for child in tree["children"]:
            stream.write(" ")
            dump_tree_ABCT(child, stream)
        # === END FOR child ===

        stream.write(")")
    else:
        if "surf" in tree:
            stream.write(
                f"({cat} {tree['surf']})"
            )
        elif "word" in tree:
            stream.write(
                f"({cat} {tree['word']})"
            )
        else:
            stream.write(
                f"({cat} ERROR)"
            )
    # === END IF ===
# === END ===

# ======
# 1. Category Parser and Translators
# ======
"""
A tranalation table that translates atomic categories in the depccg format
    to those in the ABC Treebank format.
In fact, what this does is just get rid of brackets.

Examples
--------
"S[m]" -> "Sm"
"""
pCAT_BASE_trans_table: typing.Dict[int, str] = (
    str.maketrans(
        {
            "[": "",
            "]": ""    
        }
    )
)

@parsy.generate
def pCAT_BASE():
    """
    A parsy parser and translator of atomic depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]" -> {"type": "BASE", "lit": "Sm"}
    """

    cat = yield parsy.regex(r"[^()\\/]+")

    return {
        "type": "BASE",
        "lit": cat.translate(pCAT_BASE_trans_table)
    }
# === END ===

@parsy.generate
def pCAT_COMP_LEFT():
    """
    A parsy parser and translator of left-functor depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]\\PP[s]\\PP[o]" -> 
    {
        "type": "L", 
        "antecedent": {
                "type": "Base",
                "lit": "PPo",
            }, 
        "consequence": {
            "type": "L":
            "antecedent": {
                "type": "Base",
                "lit": "PPs",
            }, 
            "consequence": {
                "type": "Base",
                "lit": "Sm",
            }, 
        }
    """

    cat1 = yield pCAT_COMP_RIGHT 
    cat_others = yield (
        parsy.match_item("\\") 
        >> (
             pCAT_COMP_RIGHT
        )
    ).many()

    res = cat1
    for cat_next in cat_others:
        res = {
            "type": "L",
            "antecedent": cat_next,
            "consequence": res,
        }
    return res
# === END ===

@parsy.generate
def pCAT_COMP_RIGHT():
    """
    A parsy parser and translator of right-functor depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]/PP[s]/PP[o]" -> 
    {
        "type": "R", 
        "antecedent": {
                "type": "Base",
                "lit": "PPo",
            }, 
        "consequence": {
            "type": "R":
            "antecedent": {
                "type": "Base",
                "lit": "PPs",
            }, 
            "consequence": {
                "type": "Base",
                "lit": "Sm",
            }, 
        }
    """

    cat1 = yield pCAT_BASE | pCAT_PAR
    cat_others = yield (
        parsy.match_item("/") 
        >> (pCAT_BASE | pCAT_PAR)
    ).many()

    res = cat1
    for cat_next in cat_others:
        res = {
            "type": "R",
            "antecedent": cat_next,
            "consequence": res,
        }
    return res
# === END ===

@parsy.generate
def pCAT_PAR():
    """
    A parsy parser and translator of parenthesized depccg categories 
        into abstract representations of CG categories.
    """

    yield parsy.match_item("(")
    cat = yield pCAT
    yield parsy.match_item(")")

    return cat
# === END ===

"""
The root paraser and translator of any depccg categories 
    into abstract representations of CG categories.
"""
pCAT = pCAT_COMP_LEFT

def parse_cat(text: str) -> dict:
    """
    Parse powered by parsy an depccg category and translate it into an abstract representation for CG categories.

    Parameters
    ----------
    text : str
        A string representation of an depccg category.
    
    Returns
    -------
    res : dict
        An abstract representation of the given input.

    Examples
    --------
    >>> parse_cat("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])")
    {'type': 'R',
        'antecedent': {'type': 'L',
            'antecedent': {'type': 'BASE', 'lit': 'PPo'},
            'consequence': {'type': 'L',
                'antecedent': {'type': 'BASE', 'lit': 'PPs'},
                'consequence': {'type': 'BASE', 'lit': 'Sp'}}},
        'consequence': {'type': 'R',
            'antecedent': {'type': 'BASE', 'lit': 'Sm'},
            'consequence': {'type': 'BASE', 'lit': 'Sm'}}}
    """

    return pCAT.parse(text)
# === END ===

def translate_cat_TLG(cat: dict) -> str:
    """
    Print an abstract representation of a CG category in the ABC Treebank format.

    Parameters
    ----------
    cat : dict
        An abstract representation of a CG category.
    
    Returns
    -------
    res : str
        A string representation in the ABC Treebank format.


    Examples
    --------
    >>> translate_cat_TLG(parse_cat("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])"))
    '<<Sm/Sm>/<PPo\\<PPs\\Sp>>>'
    """

    input_type = cat["type"]
    if input_type == "L":
        return f"<{translate_cat_TLG(cat['antecedent'])}\{translate_cat_TLG(cat['consequence'])}>"
    elif input_type == "R":
        return f"<{translate_cat_TLG(cat['consequence'])}/{translate_cat_TLG(cat['antecedent'])}>"
    else:
        return cat["lit"]
    # === END IF ===
# === END ===

def parse_cat_translate_TLG(text: str):
    """
    Print an abstract representation of a CG category in the ABC Treebank format.

    Parameters
    ----------
    text : str
        A string representation of an depccg category.
    
    Returns
    -------
    res : str
        A string representation in the ABC Treebank format.

    Examples
    --------
    >>> parse_cat_translate_TLG("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])"))
    '<<Sm/Sm>/<PPo\\<PPs\\Sp>>>'

    Notes
    --------
    parse_cat_translate_TLG(str) == translate_cat_TLG(parse_cat(str))

    """
    return translate_cat_TLG(parse_cat(text))
# === END ===



def main(args):

    

    # 解析
    parsed_trees = parser.parse_doc(doc, batchsize=args.batchsize)
        
    # 木を出力
    if args.format == "abct":
        for i, (parsed, tokens) in enumerate(zip(parsed_trees, tagged_doc), 1):
            for tree, prob in parsed:
                tree_enh = {
                    "type": "ROOT",
                    "cat": "TOP",
                    "children": [
                        {
                            "cat": "COMMENT",
                            "surf": f"{{probability={prob}}}"
                        },
                        tree.json(tokens = tokens),
                        {
                            "cat": "ID",
                            "surf": str(i)
                        }
                    ]
                }
                dump_tree_ABCT(tree_enh, sys.stdout)
                sys.stdout.write("\n")
            # === END FOR ===
        # === END FOR ===
    else:
        print_(parsed_trees, tagged_doc, format=args.format, lang='ja')
    # === END IF ===
# === END ===